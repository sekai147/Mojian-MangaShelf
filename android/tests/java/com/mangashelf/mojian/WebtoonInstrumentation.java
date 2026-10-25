package com.mangashelf.mojian;

import android.app.*;
import android.content.*;
import android.content.pm.ActivityInfo;
import android.graphics.*;
import android.graphics.pdf.PdfDocument;
import android.os.*;
import android.view.*;
import java.io.*;
import java.util.*;

/** Runs after the ordinary reader suite, in the same disposable test installation. */
public class WebtoonInstrumentation extends Instrumentation {
    MainActivity activity;final ArrayList<String> passed=new ArrayList<>();
    @Override public void onCreate(Bundle args){super.onCreate(args);start();}
    void check(boolean value,String reason){if(!value)throw new AssertionError(reason);}
    void ui(Runnable r){runOnMainSync(r);waitForIdleSync();}
    void ok(String name){passed.add(name);Bundle b=new Bundle();b.putString("stream","PASS "+name+"\n");sendStatus(0,b);}
    void settle()throws Exception{
        long end=SystemClock.uptimeMillis()+25000;
        while(SystemClock.uptimeMillis()<end){waitForIdleSync();WebtoonView view=activity.webtoonView;
            if(view!=null&&view.ready&&view.announced&&view.pending.isEmpty()){ui(view::flushPosition);return;}
            Thread.sleep(60);
        }throw new AssertionError("Webtoon loading timeout");
    }
    void screenshot(String name)throws Exception{
        ui(()->{if(activity.lastToast!=null)activity.lastToast.cancel();});Thread.sleep(1200);waitForIdleSync();
        Bitmap bitmap=getUiAutomation().takeScreenshot();
        try(OutputStream out=new FileOutputStream(new File(getTargetContext().getExternalFilesDir(null),name+".png"))){bitmap.compress(Bitmap.CompressFormat.PNG,100,out);}bitmap.recycle();
    }
    void swipeUp()throws Exception{
        int[] xy=new int[2];ui(()->activity.webtoonView.getLocationOnScreen(xy));
        float x=xy[0]+activity.webtoonView.getWidth()*.5f,y=xy[1]+activity.webtoonView.getHeight()*.8f;
        long now=SystemClock.uptimeMillis();sendPointerSync(MotionEvent.obtain(now,now,0,x,y,0));
        for(int i=1;i<=10;i++){Thread.sleep(20);sendPointerSync(MotionEvent.obtain(now,SystemClock.uptimeMillis(),2,x,y-activity.webtoonView.getHeight()*.55f*i/10,0));}
        sendPointerSync(MotionEvent.obtain(now,SystemClock.uptimeMillis(),1,x,xy[1]+activity.webtoonView.getHeight()*.25f,0));
        Thread.sleep(500);ui(()->activity.webtoonView.scroller.abortAnimation());settle();
    }
    Library.Book tallBook()throws Exception{
        Library.Book book=new Library.Book();book.title=book.folder="条漫长页验证";book.source="test:webtoon";
        File folder=new File(activity.library.booksDir,book.id);check(folder.mkdirs(),"Fixture directory");
        File file=new File(folder,"long.pdf");PdfDocument pdf=new PdfDocument();
        try{
            for(int i=0;i<2;i++){
                PdfDocument.Page page=pdf.startPage(new PdfDocument.PageInfo.Builder(300,9000,i+1).create());
                Canvas c=page.getCanvas();c.drawColor(Color.rgb(160,190,160));Paint p=new Paint();p.setColor(Color.rgb(80,145,190));c.drawRect(0,4500,300,9000,p);pdf.finishPage(page);
            }try(OutputStream out=new FileOutputStream(file)){pdf.writeTo(out);}
        }finally{pdf.close();}
        Library.Chapter chapter=new Library.Chapter();chapter.name="超长章节";chapter.path=book.id+"/long.pdf";chapter.source="long.pdf";chapter.pages=2;book.chapters.add(chapter);ui(()->{try{activity.library.commit(book);}catch(Exception e){throw new RuntimeException(e);}});return book;
    }
    @Override public void onStart(){Bundle result=new Bundle();try{
        activity=(MainActivity)startActivitySync(new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        ui(()->activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT));Thread.sleep(700);
        check(!activity.library.books.isEmpty(),"Run ordinary reader suite first");Library.Book book=activity.library.books.get(0);check(book.title.equals("森间来信 · 我的收藏"),"Upgrade preserves customized book name");
        ui(()->activity.prefs.edit().putString("layout","single").apply());ui(()->activity.openReader(book,0,0));
        Thread.sleep(300);ui(()->activity.setReaderLayout("webtoon"));settle();
        check(activity.pageView==null&&activity.webtoonView!=null,"Separate continuous reader active");
        check(activity.webtoonView.pages.size()==book.totalPages(),"All chapter pages form one stream");
        check(activity.layoutName().equals("条漫模式"),"Mode label");
        for(int i=1;i<activity.webtoonView.pages.size();i++){WebtoonView.Page a=activity.webtoonView.pages.get(i-1),b=activity.webtoonView.pages.get(i);check(Math.abs(a.top+a.ratio-b.top)<1e-10,"Pages meet without synthetic margins");}
        ok("webtoon_mode_continuous_width_fitted_pages");
        ui(()->activity.webtoonView.jumpTo(0,0,.75));settle();screenshot("webtoon-continuous");
        double before=activity.webtoonView.offset;swipeUp();check(activity.webtoonView.offset>before+.1,"Actual upward gesture scrolls down");ok("webtoon_real_vertical_touch_scroll");
        ui(()->activity.webtoonView.jumpTo(0,book.chapters.get(0).pages-1,.9));settle();ui(()->activity.webtoonView.scrollByPixels(activity.webtoonView.getHeight()));settle();
        check(activity.chapterIndex>0,"Continuous scroll crosses chapter boundary");check(activity.readerChapterLabel.getText().toString().equals(book.chapters.get(activity.chapterIndex).name),"Chapter header follows scroll");ok("webtoon_continuous_cross_chapter_and_header");
        ui(()->activity.webtoonView.jumpTo(1,0,.37));settle();ui(()->activity.closeReader());
        Library restored=new Library(getTargetContext());Library.Book saved=restored.books.get(0);check(saved.index()==1&&saved.page==0&&Math.abs(saved.scrollFraction-.37)<.01,"Exact in-page position saved");
        ui(()->activity.openReader(book,book.index(),book.page));settle();check(Math.abs(activity.webtoonView.lastFraction-.37)<.01,"Position restored on reopen");
        check(activity.prefs.getString("layout","").equals("webtoon"),"Mode persisted");ok("webtoon_fractional_progress_and_mode_persist");
        double fraction=activity.webtoonView.lastFraction;ui(()->activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE));Thread.sleep(650);settle();
        check(activity.webtoonView!=null&&!activity.dual(),"Rotation keeps webtoon");check(Math.abs(activity.webtoonView.lastFraction-fraction)<.01,"Rotation preserves reading anchor");ok("webtoon_rotation_preserves_mode_and_position");
        ui(()->activity.readerChapters());getUiAutomation().performGlobalAction(1);waitForIdleSync();
        ui(()->{activity.chapterIndex=2;activity.page=0;activity.renderPage(0,true);});settle();check(activity.chapterIndex==2&&activity.page==0,"Chapter/page jump in continuous mode");
        ui(()->activity.step(1));settle();check(activity.page==1,"Next page control works");ok("webtoon_directory_jump_and_page_controls");
        ui(()->activity.setReaderLayout("dual"));long wait=SystemClock.uptimeMillis()+20000;while(SystemClock.uptimeMillis()<wait&&(activity.pageView==null||activity.pageView.bitmap==null)){Thread.sleep(40);waitForIdleSync();}
        check(activity.webtoonView==null&&activity.pageView!=null&&activity.pageView.bitmap!=null,"Switch back to paged rendering");check(activity.chapterIndex==2,"Mode switch keeps chapter");ok("webtoon_switch_back_to_double_page");
        ui(()->activity.closeReader());Library.Book longBook=tallBook();ui(()->{activity.prefs.edit().putString("layout","webtoon").apply();activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);activity.openReader(longBook,0,0);});Thread.sleep(600);settle();
        check(longBook.progress()<.001,"Long page is not marked read merely by opening it");
        ui(()->activity.webtoonView.jumpTo(0,0,.7));settle();
        WebtoonView view=activity.webtoonView;int width=view.rasterWidth();WebtoonView.Page p=view.pages.get(0);long row=(long)Math.floor((view.offset-p.top)*width/WebtoonView.TILE_HEIGHT);
        WebtoonView.Tile tile=view.cache.get(view.key(0,width,row));check(tile!=null,"Long-page reading tile loaded");
        check(tile.bitmap.getPixel(5,5)==Color.rgb(80,145,190),"Tile transform renders actual lower-page content");
        check(tile.bitmap.getHeight()<=1024,"Long page is tiled");check(view.cacheBytes<=WebtoonView.CACHE_LIMIT,"Raster cache bound");ok("webtoon_long_pdf_tiles_correct_pixels_and_bounded_memory");
        ui(()->activity.webtoonView.setZoom(2.5f,activity.webtoonView.getWidth()/2f,activity.webtoonView.getHeight()/2f));settle();check(activity.webtoonView.zoom>2,"Zoom supported");check(activity.webtoonView.cacheBytes<=WebtoonView.CACHE_LIMIT,"Zoom keeps cache bound");
        ui(()->activity.webtoonView.setZoom(1,activity.webtoonView.getWidth()/2f,0));settle();ui(()->activity.toggleTools());settle();ui(()->activity.toggleTools());settle();ok("webtoon_zoom_and_immersive_controls");
        ui(()->activity.webtoonView.scrollByPixels(1e9));settle();check(longBook.progress()==1&&longBook.scrollFinished,"Reaching the stream end marks read");
        ui(()->activity.webtoonView.jumpTo(0,0,.25));settle();check(longBook.progress()<.2&&!longBook.scrollFinished,"Reading earlier updates fractional progress");ok("webtoon_fractional_completion_and_end_of_book");
        ui(()->activity.webtoonView.jumpTo(0,0,.65));settle();screenshot("webtoon-tall-pdf");ui(()->activity.readerOptions());screenshot("webtoon-options");getUiAutomation().performGlobalAction(1);waitForIdleSync();ui(()->activity.closeReader());
        ui(()->activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED));
        result.putString("stream",passed.size()+" webtoon checks passed\n"+String.join("\n",passed));finish(Activity.RESULT_OK,result);
    }catch(Throwable e){try{screenshot("webtoon-failure");}catch(Exception ignored){}StringWriter trace=new StringWriter();e.printStackTrace(new PrintWriter(trace));result.putString("stream","FAILED\n"+trace);finish(Activity.RESULT_CANCELED,result);}}
}
