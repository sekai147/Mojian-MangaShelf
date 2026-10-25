package com.mangashelf.mojian;

import android.content.Context;
import android.graphics.*;
import android.graphics.pdf.PdfRenderer;
import android.os.*;
import android.view.*;
import android.view.accessibility.AccessibilityNodeInfo;
import android.widget.OverScroller;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

/** A continuous, width-fitted PDF canvas. Only nearby raster tiles occupy memory. */
final class WebtoonView extends View {
    interface Listener {
        void position(int chapter, int page, double fraction, boolean end);
        void ready();
        void error(String message);
        void toggleTools();
    }

    static final int TILE_HEIGHT = 1024;
    static final long CACHE_LIMIT = 24L * 1024 * 1024;
    static final class Page {
        final File file;
        final int chapter, number, width, height;
        final double top, ratio;
        Page(File file, int chapter, int number, int width, int height, double top) {
            this.file=file; this.chapter=chapter; this.number=number;
            this.width=width; this.height=height; this.top=top;
            ratio=(double)height/width;
        }
    }
    static final class Tile {
        final int page, width;
        final long row;
        final Bitmap bitmap;
        Tile(int page,int width,long row,Bitmap bitmap) {
            this.page=page;this.width=width;this.row=row;this.bitmap=bitmap;
        }
    }

    final Library library;
    final Library.Book book;
    final Listener listener;
    final Handler main=new Handler(Looper.getMainLooper());
    final ExecutorService worker=Executors.newSingleThreadExecutor();
    final LinkedHashMap<String,Tile> cache=new LinkedHashMap<>(16,.75f,true);
    final Map<String,Future<?>> pending=new HashMap<>();
    final Set<String> wanted=new HashSet<>(), visible=new HashSet<>(), failed=new HashSet<>();
    final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
    final Paint text=new Paint(Paint.ANTI_ALIAS_FLAG);
    final OverScroller scroller;
    final GestureDetector gestures;
    final ScaleGestureDetector scales;
    final Runnable report=this::flushPosition;
    List<Page> pages=Collections.emptyList();
    double offset=0, total=0;
    float zoom=1, panX=0;
    int pendingChapter, pendingPage, lastScrollerY=0;
    double pendingFraction;
    long cacheBytes=0;
    boolean ready=false, disposed=false, announced=false;
    int lastChapter=-1, lastPage=-1;
    double lastFraction=-1;
    boolean lastEnd=false;

    WebtoonView(Context context, Library library, Library.Book book, int chapter, int page,
                double fraction, Listener listener) {
        super(context);
        this.library=library;this.book=book;this.listener=listener;
        pendingChapter=chapter;pendingPage=page;pendingFraction=fraction;
        setBackgroundColor(Color.WHITE);setFocusable(true);
        setContentDescription("条漫阅读；上下滑动连续阅读，双指缩放，轻点显示工具栏");
        text.setTextSize(Ui.dp(context,13));text.setColor(Ui.MUTED);
        text.setTextAlign(Paint.Align.CENTER);
        scroller=new OverScroller(context);
        scales=new ScaleGestureDetector(context,new ScaleGestureDetector.SimpleOnScaleGestureListener(){
            @Override public boolean onScaleBegin(ScaleGestureDetector d){scroller.abortAnimation();return ready;}
            @Override public boolean onScale(ScaleGestureDetector d){
                setZoom(zoom*d.getScaleFactor(),d.getFocusX(),d.getFocusY());return true;
            }
        });
        gestures=new GestureDetector(context,new GestureDetector.SimpleOnGestureListener(){
            @Override public boolean onDown(MotionEvent e){scroller.abortAnimation();return true;}
            @Override public boolean onScroll(MotionEvent a,MotionEvent b,float dx,float dy){
                if(!scales.isInProgress()){panX-=dx;scrollByPixels(dy);}return true;
            }
            @Override public boolean onFling(MotionEvent a,MotionEvent b,float vx,float vy){
                if(!ready||scales.isInProgress())return false;
                lastScrollerY=0;scroller.fling(0,0,0,(int)-vy,0,0,-1_000_000,1_000_000);
                postInvalidateOnAnimation();return true;
            }
            @Override public boolean onSingleTapConfirmed(MotionEvent e){
                if(!failed.isEmpty()){failed.clear();invalidate();}
                else listener.toggleTools();
                performClick();return true;
            }
            @Override public boolean onDoubleTap(MotionEvent e){
                setZoom(zoom>1.05f?1:2,e.getX(),e.getY());return true;
            }
        });
        worker.submit(this::loadPages);
    }

    void loadPages() {
        ArrayList<Page> result=new ArrayList<>();double top=0;
        try {
            for(int c=0;c<book.chapters.size();c++) {
                if(Thread.currentThread().isInterrupted())return;
                File file=library.file(book.chapters.get(c));
                try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(file,ParcelFileDescriptor.MODE_READ_ONLY);
                    PdfRenderer pdf=new PdfRenderer(fd)) {
                    for(int p=0;p<pdf.getPageCount();p++) {
                        if(Thread.currentThread().isInterrupted())return;
                        try(PdfRenderer.Page source=pdf.openPage(p)) {
                            Page entry=new Page(file,c,p,source.getWidth(),source.getHeight(),top);
                            result.add(entry);top+=entry.ratio;
                        }
                    }
                }
            }
            if(result.isEmpty())throw new IOException("漫画没有可阅读页面");
            final double height=top;
            main.post(()->{
                if(disposed)return;pages=result;total=height;ready=true;
                jumpTo(pendingChapter,pendingPage,pendingFraction);
            });
        } catch(Exception|OutOfMemoryError e) {
            main.post(()->{if(!disposed)listener.error("无法展开条漫，请检查 PDF 文件后重试");});
        }
    }

    double scale(){return Math.max(1,getWidth())*(double)zoom;}
    double maxOffset(){return Math.max(0,total-getHeight()/scale());}
    void clamp(){offset=Math.max(0,Math.min(maxOffset(),offset));panX=Math.max((float)(getWidth()-scale()),Math.min(0,panX));}

    void setZoom(float value,float focusX,float focusY) {
        if(!ready)return;
        scroller.abortAnimation();double oldScale=scale();
        double anchor=offset+focusY/oldScale;
        double x=(focusX-panX)/oldScale;
        zoom=Math.max(1,Math.min(3,value));
        offset=anchor-focusY/scale();panX=(float)(focusX-x*scale());
        clamp();changed();
    }

    void scrollByPixels(double pixels) {
        if(!ready)return;offset+=pixels/scale();clamp();changed();
    }

    void jumpTo(int chapter,int number,double fraction) {
        pendingChapter=chapter;pendingPage=number;
        pendingFraction=Math.max(0,Math.min(.999999,fraction));
        if(!ready)return;
        scroller.abortAnimation();
        int target=0;
        for(int i=0;i<pages.size();i++) {
            Page p=pages.get(i);
            if(p.chapter==chapter&&p.number<=number)target=i;
            if(p.chapter==chapter&&p.number==number)break;
        }
        Page p=pages.get(target);offset=p.top+p.ratio*pendingFraction;
        clamp();changed();
    }

    int pageAt(double position) {
        int low=0,high=pages.size()-1;
        while(low<high){int mid=(low+high+1)/2;if(pages.get(mid).top<=position)low=mid;else high=mid-1;}
        return low;
    }

    int rasterWidth(){return Math.max(128,Math.min(1536,(int)Math.ceil(scale())));}
    String key(int page,int width,long row){return page+":"+width+":"+row;}

    void changed(){
        invalidate();main.removeCallbacks(report);main.postDelayed(report,140);
    }

    void flushPosition(){
        if(!ready||disposed||pages.isEmpty()||getWidth()==0)return;
        int index=pageAt(offset+1e-8);Page p=pages.get(index);
        double fraction=Math.max(0,Math.min(.999999,(offset-p.top)/p.ratio));
        long row=(long)Math.floor((offset-p.top)*rasterWidth()/TILE_HEIGHT);
        // Reading progress advances only once pixels at the reading position are available.
        if(!cache.containsKey(key(index,rasterWidth(),Math.max(0,row))))return;
        if(!announced){announced=true;listener.ready();}
        boolean end=offset>=maxOffset()-1/scale();
        if(lastChapter==p.chapter&&lastPage==p.number&&Math.abs(lastFraction-fraction)<.00005&&lastEnd==end)return;
        lastChapter=p.chapter;lastPage=p.number;lastFraction=fraction;lastEnd=end;
        setContentDescription("条漫阅读，第 "+(p.chapter+1)+" 章，第 "+(p.number+1)+" 页；上下滑动连续阅读");
        listener.position(p.chapter,p.number,fraction,end);
    }

    @Override protected void onSizeChanged(int w,int h,int oldw,int oldh){
        super.onSizeChanged(w,h,oldw,oldh);if(ready){clamp();changed();}
    }
    @Override public boolean onTouchEvent(MotionEvent e){
        scales.onTouchEvent(e);gestures.onTouchEvent(e);return true;
    }
    @Override public boolean performClick(){super.performClick();return true;}
    @Override public void computeScroll(){
        if(scroller.computeScrollOffset()){
            int y=scroller.getCurrY();double before=offset;
            scrollByPixels(y-lastScrollerY);lastScrollerY=y;
            if(Math.abs(before-offset)<1e-10)scroller.abortAnimation();
            else postInvalidateOnAnimation();
        }
    }

    @Override protected void onDraw(Canvas canvas){
        super.onDraw(canvas);if(!ready||disposed||getWidth()==0)return;
        double s=scale();int width=rasterWidth();double bottom=offset+getHeight()/s;
        int first=pageAt(offset),last=pageAt(Math.min(total,bottom));
        wanted.clear();
        // At most one viewport beyond the visible region is prefetched.
        int preFirst=pageAt(Math.max(0,offset-getHeight()/s*.35));
        int preLast=pageAt(Math.min(total,bottom+getHeight()/s*.6));
        for(int i=first;i<=last;i++) {
            Page p=pages.get(i);
            long start=Math.max(0,(long)Math.floor((offset-p.top)*width/TILE_HEIGHT));
            long end=(long)Math.floor(Math.min(p.ratio,bottom-p.top)*width/TILE_HEIGHT);
            long maxRow=Math.max(0,((long)Math.ceil(p.ratio*width)-1)/TILE_HEIGHT);
            end=Math.min(end,maxRow);
            for(long row=start;row<=end;row++) {
                String key=key(i,width,row);wanted.add(key);Tile tile=cache.get(key);
                float y=(float)((p.top-offset)*s+row*TILE_HEIGHT*s/width);
                if(tile!=null){float height=(float)(tile.bitmap.getHeight()*s/width);canvas.drawBitmap(tile.bitmap,null,new RectF(panX,y,(float)(panX+s),y+height),paint);}
                else {
                    float height=(float)(Math.min(TILE_HEIGHT,p.ratio*width-row*TILE_HEIGHT)*s/width);
                    float baseline=Math.max(24,Math.min(getHeight()-24,y+height/2));
                    canvas.drawText(failed.contains(key)?"加载失败，轻点重试":"正在加载…",getWidth()/2f,baseline,text);
                }
            }
        }
        visible.clear();visible.addAll(wanted);
        // Cancel work that a fast fling has already moved past, before enqueueing new tiles.
        double preTop=Math.max(0,offset-getHeight()/s*.35),preBottom=Math.min(total,bottom+getHeight()/s*.6);
        for(int i=preFirst;i<=preLast;i++) {
            Page p=pages.get(i);long start=Math.max(0,(long)Math.floor((preTop-p.top)*width/TILE_HEIGHT));
            long end=Math.min((long)Math.floor((preBottom-p.top)*width/TILE_HEIGHT),Math.max(0,((long)Math.ceil(p.ratio*width)-1)/TILE_HEIGHT));
            for(long row=start;row<=end;row++)wanted.add(key(i,width,row));
        }
        Iterator<Map.Entry<String,Future<?>>> iterator=pending.entrySet().iterator();
        while(iterator.hasNext()){Map.Entry<String,Future<?>> e=iterator.next();if(!wanted.contains(e.getKey())){e.getValue().cancel(false);iterator.remove();}}
        // Visible tiles are submitted first.
        for(int i=first;i<=last;i++)requestRange(i,width,offset,bottom);
        for(int i=preFirst;i<=preLast;i++)requestRange(i,width,preTop,preBottom);
    }

    void requestRange(int index,int width,double from,double to){
        Page p=pages.get(index);
        long start=Math.max(0,(long)Math.floor((from-p.top)*width/TILE_HEIGHT));
        long end=Math.min((long)Math.floor((to-p.top)*width/TILE_HEIGHT),Math.max(0,((long)Math.ceil(p.ratio*width)-1)/TILE_HEIGHT));
        for(long row=start;row<=end;row++)requestTile(index,width,row);
    }

    void requestTile(int index,int width,long row){
        String id=key(index,width,row);
        if(disposed||cache.containsKey(id)||pending.containsKey(id)||failed.contains(id))return;
        if(!visible.contains(id)&&cacheBytes+pending.size()*(long)width*TILE_HEIGHT*4>CACHE_LIMIT*.7)return;
        Page p=pages.get(index);
        Future<?> job=worker.submit(()->{
            Bitmap bitmap=null;
            try {
                int height=(int)Math.min(TILE_HEIGHT,(long)Math.ceil(p.ratio*width)-row*TILE_HEIGHT);
                bitmap=Bitmap.createBitmap(width,Math.max(1,height),Bitmap.Config.ARGB_8888);
                bitmap.eraseColor(Color.WHITE);
                try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(p.file,ParcelFileDescriptor.MODE_READ_ONLY);
                    PdfRenderer pdf=new PdfRenderer(fd);PdfRenderer.Page source=pdf.openPage(p.number)) {
                    Matrix transform=new Matrix();float factor=(float)width/p.width;
                    transform.setValues(new float[]{factor,0,0,0,factor,(float)(-row*TILE_HEIGHT),0,0,1});
                    source.render(bitmap,null,transform,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                }
                Bitmap pixels=bitmap;
                main.post(()->{
                    pending.remove(id);
                    if(disposed||!wanted.contains(id)){pixels.recycle();return;}
                    Tile old=cache.put(id,new Tile(index,width,row,pixels));
                    if(old!=null){cacheBytes-=old.bitmap.getAllocationByteCount();old.bitmap.recycle();}
                    cacheBytes+=pixels.getAllocationByteCount();trim();invalidate();flushPosition();
                });
            }catch(Exception|OutOfMemoryError e){
                if(bitmap!=null&&!bitmap.isRecycled())bitmap.recycle();
                main.post(()->{pending.remove(id);if(!disposed){failed.add(id);invalidate();if(!announced)listener.error("页面加载失败，轻点页面重试");}});
            }
        });
        pending.put(id,job);
    }

    void trim(){
        Iterator<Map.Entry<String,Tile>> it=cache.entrySet().iterator();
        while(cacheBytes>CACHE_LIMIT&&it.hasNext()){
            Map.Entry<String,Tile> entry=it.next();if(visible.contains(entry.getKey()))continue;
            Tile tile=entry.getValue();it.remove();cacheBytes-=tile.bitmap.getAllocationByteCount();tile.bitmap.recycle();
        }
        it=cache.entrySet().iterator();
        while(cacheBytes>CACHE_LIMIT&&it.hasNext()){
            Tile tile=it.next().getValue();it.remove();cacheBytes-=tile.bitmap.getAllocationByteCount();tile.bitmap.recycle();
        }
    }
    @Override public void onInitializeAccessibilityNodeInfo(AccessibilityNodeInfo info){
        super.onInitializeAccessibilityNodeInfo(info);info.setScrollable(true);
        info.addAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_FORWARD);
        info.addAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_BACKWARD);
    }
    @Override public boolean performAccessibilityAction(int action,Bundle arguments){
        if(action==AccessibilityNodeInfo.ACTION_SCROLL_FORWARD||action==AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD){scrollByPixels(getHeight()*.8*(action==AccessibilityNodeInfo.ACTION_SCROLL_FORWARD?1:-1));return true;}
        return super.performAccessibilityAction(action,arguments);
    }
    void dispose(){
        if(disposed)return;flushPosition();disposed=true;main.removeCallbacks(report);
        scroller.abortAnimation();worker.shutdownNow();pending.clear();wanted.clear();
        for(Tile tile:cache.values())tile.bitmap.recycle();cache.clear();cacheBytes=0;
    }
}
