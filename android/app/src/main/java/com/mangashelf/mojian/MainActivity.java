package com.mangashelf.mojian;

import android.app.*;
import android.content.*;
import android.content.res.Configuration;
import android.graphics.*;
import android.graphics.drawable.ColorDrawable;
import android.net.Uri;
import android.os.*;
import android.text.*;
import android.view.*;
import android.view.inputmethod.EditorInfo;
import android.widget.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import static com.mangashelf.mojian.Ui.*;

public class MainActivity extends Activity {
    Library library;android.content.SharedPreferences prefs;
    final ExecutorService importer=Executors.newSingleThreadExecutor(), renderer=Executors.newSingleThreadExecutor(), covers=Executors.newSingleThreadExecutor();
    final Handler main=new Handler(Looper.getMainLooper());Future<?> renderJob;
    FrameLayout root;LinearLayout screen,grid,readerHeader,readerFooter;PageView pageView;TextView pageLabel,readerTitle,readerChapterLabel,loading;
    WebtoonView webtoonView;FrameLayout readerStage;
    FrameLayout headerSlot,footerSlot;ReaderChromeMotion chromeMotion;
    final Runnable saveWebtoon=()->{if(!this.dead&&library!=null)persist();};
    SeekBar seek;Library.Book active,detail;int chapterIndex=0,page=0,request=0,tab=0;String filter="";
    boolean busy=false,dead=false,chrome=true;volatile boolean cancelImport=false;
    Dialog busyDialog;TextView importMessage;String location="library";int libraryGeneration=0;Toast lastToast;
        final Map<String,Bitmap> coverCache=new LinkedHashMap<String,Bitmap>(32,.75f,true){protected boolean removeEldestEntry(Map.Entry<String,Bitmap> entry){return size()>24;}};

    @Override public void onCreate(Bundle state){
        super.onCreate(state);prefs=getSharedPreferences("reading",MODE_PRIVATE);
        try{library=new Library(this);}catch(Exception e){new AlertDialog.Builder(this).setTitle("书库暂时无法打开").setMessage("请保留应用数据后重试。\n"+e.getMessage()).setPositiveButton("关闭",(d,w)->finish()).setCancelable(false).show();return;}
        root=new FrameLayout(this);root.setBackgroundColor(BG);setContentView(root);
        root.setOnApplyWindowInsetsListener((v,insets)->{
            if(Build.VERSION.SDK_INT>=30){android.graphics.Insets b=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());v.setPadding(b.left,b.top,b.right,b.bottom);}
            else v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });root.requestApplyInsets();
        if(state!=null){String id=state.getString("book");for(Library.Book b:library.books)if(b.id.equals(id))active=b;}
        if(active!=null)openReader(active,active.index(),active.page);else showLibrary();
    }
    @Override public void onSaveInstanceState(Bundle out){super.onSaveInstanceState(out);if(active!=null)out.putString("book",active.id);}
    @Override public void onConfigurationChanged(Configuration c){super.onConfigurationChanged(c);if(webtoonView!=null){fitReaderControls();}else if(pageView!=null){fitReaderControls();root.post(()->renderPage(0,false));}else if(location.equals("library"))showLibrary();}
    @Override public void onPause(){super.onPause();if(webtoonView!=null)webtoonView.flushPosition();main.removeCallbacks(saveWebtoon);if(library!=null)persist();}
    @Override public void onDestroy(){dead=true;request++;disposeReaderViews();importer.shutdownNow();renderer.shutdownNow();covers.shutdownNow();if(busyDialog!=null)busyDialog.dismiss();for(Bitmap b:coverCache.values())if(!b.isRecycled())b.recycle();coverCache.clear();super.onDestroy();}
    @Override public void onBackPressed(){if(busy){cancelImport=true;return;}if(location.equals("reader")){closeReader();return;}if(!location.equals("library")){detail=null;showLibrary();return;}super.onBackPressed();}
    void persist(){try{library.save();}catch(Exception e){toast("进度保存失败，请检查剩余空间");}}
    void toast(String text){if(lastToast!=null)lastToast.cancel();lastToast=Toast.makeText(this,text,Toast.LENGTH_SHORT);lastToast.show();}
    void error(String title,Exception e){if(!dead)new AlertDialog.Builder(this).setTitle(title).setMessage(e.getMessage()==null?"请重试":e.getMessage()).setPositiveButton("知道了",null).show();}
    LinearLayout base(String where){
        location=where;libraryGeneration++;root.removeAllViews();screen=column(this);root.addView(screen,new FrameLayout.LayoutParams(-1,-1));screen.setBackgroundColor(BG);
        if(prefs.getBoolean("motion",true)){screen.setAlpha(0);screen.setTranslationY(dp(this,8));screen.animate().alpha(1).translationY(0).setDuration(190).start();}return screen;
    }
    void label(LinearLayout parent,String text,int size,int color,boolean bold){parent.addView(Ui.text(this,text,size,color,bold),lp(this,-1,-2));}
    LinearLayout heading(String title,Runnable back){
        LinearLayout row=row(this);pad(row,16,8);if(back!=null)row.addView(iconButton(this,"back","返回",back),lp(this,48,48));
        TextView t=text(this,title,22,INK,true);row.addView(t,new LinearLayout.LayoutParams(0,dp(this,48),1));return row;
    }
    ScrollView scroller(LinearLayout parent,boolean weighted){ScrollView s=new ScrollView(this);s.setFillViewport(false);s.setClipToPadding(false);s.setVerticalScrollBarEnabled(false);parent.addView(s,weighted?new LinearLayout.LayoutParams(-1,0,1):lp(this,-1,-1));return s;}
    void bottom(LinearLayout parent,String selected){
        LinearLayout bar=row(this);pad(bar,18,8);bar.setBackgroundColor(BG);
        String[] names={"book","folder","settings"},titles={"书架","导入","偏好"};
        for(int i=0;i<3;i++){final int index=i;LinearLayout item=column(this);item.setGravity(Gravity.CENTER);ripple(item,titles[i].equals(selected)?SOFT:BG,16);Icon icon=new Icon(this,names[i],titles[i].equals(selected)?GREEN:MUTED);item.addView(icon,lp(this,24,24));TextView t=text(this,titles[i],11,titles[i].equals(selected)?GREEN:MUTED,titles[i].equals(selected));t.setGravity(Gravity.CENTER);item.addView(t,lp(this,-1,20));item.setOnClickListener(v->{if(index==0)showLibrary();else if(index==1)pickFolder(false);else showSettings();});bar.addView(item,new LinearLayout.LayoutParams(0,dp(this,56),1));}parent.addView(bar,lp(this,-1,-2));
    }
    void showLibrary(){
        active=null;base("library");getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        LinearLayout top=row(this);pad(top,24,14);ImageView mark=new ImageView(this);mark.setImageResource(R.drawable.ic_launcher);top.addView(mark,lp(this,38,38));LinearLayout word=column(this);pad(word,10,0);label(word,"墨间",20,INK,true);gap(word,4);label(word,"让故事，慢慢展开",10,MUTED,false);top.addView(word,new LinearLayout.LayoutParams(0,-2,1));top.addView(iconButton(this,"refresh","扫描书库根目录",this::scanRoot),lp(this,48,48));screen.addView(top);
        ScrollView scroll=scroller(screen,true);LinearLayout body=column(this);pad(body,24,12);scroll.addView(body);
        LinearLayout title=row(this);title.addView(text(this,"我的书架",28,INK,true),new LinearLayout.LayoutParams(0,-2,1));title.addView(button(this,"＋ 导入",true,()->pickFolder(false)));body.addView(title);gap(body,10);label(body,library.books.size()+" 本漫画  ·  本地收藏，随时翻阅",12,MUTED,false);gap(body,24);
        Library.Book recent=null;for(Library.Book b:library.books)if(b.touched>0&&(recent==null||b.touched>recent.touched))recent=b;
        if(recent!=null){Library.Book book=recent;LinearLayout banner=row(this);surface(banner,GREEN,22);pad(banner,18,16);LinearLayout left=column(this);label(left,"接着上次的故事",10,0xffcad6c7,false);gap(left,9);TextView name=text(this,book.title,17,Color.WHITE,true);name.setMaxLines(1);name.setEllipsize(TextUtils.TruncateAt.END);left.addView(name);gap(left,7);TextView chapter=text(this,book.chapters.get(book.index()).name+"  ·  "+(book.page+1)+" 页",11,0xffd0dacd,false);chapter.setSingleLine(true);chapter.setEllipsize(TextUtils.TruncateAt.END);left.addView(chapter);gap(left,13);label(left,"继续阅读  →",12,Color.WHITE,true);banner.addView(left,new LinearLayout.LayoutParams(0,-2,1));ImageView image=cover(book,64,88);LinearLayout.LayoutParams cp=lp(this,64,88);cp.leftMargin=dp(this,12);banner.addView(image,cp);banner.setOnClickListener(v->openReader(book,book.index(),book.page));body.addView(banner);gap(body,18);}
        EditText search=new EditText(this);search.setSingleLine(true);search.setTextSize(14);search.setTextColor(INK);search.setHintTextColor(MUTED);search.setHint("搜索漫画名称");search.setCompoundDrawablePadding(dp(this,8));pad(search,16,0);surface(search,SOFT,16);search.setText(filter);body.addView(search,lp(this,-1,48));gap(body,18);
        LinearLayout tabs=row(this);String[] filters={"全部","在读","已读完"};for(int i=0;i<filters.length;i++){final int pos=i;TextView t=text(this,filters[i],13,i==tab?GREEN:MUTED,i==tab);t.setGravity(Gravity.CENTER);ripple(t,i==tab?SOFT:BG,12);LinearLayout.LayoutParams p=lp(this,78,40);p.rightMargin=dp(this,8);tabs.addView(t,p);t.setOnClickListener(v->{tab=pos;showLibrary();});}body.addView(tabs);gap(body,16);
        grid=column(this);body.addView(grid);fillGrid();gap(body,20);
        search.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int c,int a){}public void onTextChanged(CharSequence s,int st,int before,int count){filter=s.toString();fillGrid();}public void afterTextChanged(Editable e){}});bottom(screen,"书架");
    }
    void fillGrid(){
        if(grid==null)return;grid.removeAllViews();ArrayList<Library.Book> shown=new ArrayList<>();for(Library.Book b:library.books)if(b.title.toLowerCase(Locale.ROOT).contains(filter.toLowerCase(Locale.ROOT))&&(tab==0||(tab==1&&b.touched>0&&b.progress()<1)||(tab==2&&b.progress()>=1)))shown.add(b);
        shown.sort((a,b)->{int n=Long.compare(b.touched,a.touched);return n==0?ChapterOrder.natural(a.title,b.title):n;});
        if(shown.isEmpty()){LinearLayout empty=column(this);empty.setGravity(Gravity.CENTER);pad(empty,24,36);Icon book=new Icon(this,"book",GREEN);empty.addView(book,lp(this,60,60));gap(empty,18);label(empty,library.books.isEmpty()?"第一本故事，从这里开始":"暂时没有匹配的漫画",17,INK,true);gap(empty,10);TextView help=text(this,library.books.isEmpty()?"选择一个漫画文件夹\n里面每个 PDF 会识别为一章":"试试其他名称或分类",13,MUTED,false);help.setGravity(Gravity.CENTER);help.setLineSpacing(dp(this,5),1);empty.addView(help);gap(empty,22);if(library.books.isEmpty())empty.addView(button(this,"选择漫画文件夹",true,()->pickFolder(false)));grid.addView(empty);return;}
        int available=getResources().getConfiguration().screenWidthDp-48;int columns=Math.max(2,Math.min(5,available/160));int width=(available-(columns-1)*16)/columns;
        LinearLayout row=null;for(int i=0;i<shown.size();i++){if(i%columns==0){row=row(this);row.setGravity(Gravity.TOP);grid.addView(row);gap(grid,22);}Library.Book book=shown.get(i);LinearLayout cell=column(this);LinearLayout.LayoutParams cellp=lp(this,width,-2);if(i%columns!=0)cellp.leftMargin=dp(this,16);row.addView(cell,cellp);cell.addView(cover(book,width,(int)(width*1.34)),lp(this,-1,(int)(width*1.34)));gap(cell,10);LinearLayout info=row(this);TextView name=text(this,book.title,14,INK,true);name.setMaxLines(1);name.setEllipsize(TextUtils.TruncateAt.END);info.addView(name,new LinearLayout.LayoutParams(0,dp(this,32),1));View more=iconButton(this,"more","管理 "+book.title,()->bookActions(book));info.addView(more,lp(this,32,40));cell.addView(info);label(cell,book.chapters.size()+" 章  ·  "+(book.touched==0?"尚未翻阅":Math.round(book.progress()*100)+"%"),11,MUTED,false);gap(cell,8);ProgressBar progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(1000);progress.setProgress((int)(book.progress()*1000));progress.setProgressTintList(android.content.res.ColorStateList.valueOf(GREEN));progress.setProgressBackgroundTintList(android.content.res.ColorStateList.valueOf(LINE));cell.addView(progress,lp(this,-1,3));cell.setOnClickListener(v->showBook(book));cell.setOnLongClickListener(v->{bookActions(book);return true;});}
    }
    ImageView cover(Library.Book book,int width,int height){
        ImageView image=new ImageView(this);image.setScaleType(ImageView.ScaleType.CENTER_CROP);surface(image,SOFT,14);image.setContentDescription(book.title+" 封面");String key=book.chapters.isEmpty()?book.id:book.chapters.get(0).path;Bitmap cached=coverCache.get(key);
        if(cached!=null&&!cached.isRecycled())image.setImageBitmap(cached);else{image.setImageResource(R.drawable.ic_launcher);image.setScaleType(ImageView.ScaleType.CENTER_INSIDE);image.setPadding(dp(this,16),dp(this,16),dp(this,16),dp(this,16));int generation=libraryGeneration;
            covers.submit(()->{try{File cache=new File(getCacheDir(),"cover-"+book.id+"-"+key.hashCode()+".jpg");Bitmap bmp;if(cache.isFile())bmp=BitmapFactory.decodeFile(cache.getPath());else{Bitmap rendered=PdfEngine.render(library.file(book.chapters.get(0)),0,false,false,200,280).bitmap;bmp=Bitmap.createScaledBitmap(rendered,256,Math.max(1,Math.round(rendered.getHeight()*256f/rendered.getWidth())),true);if(rendered!=bmp)rendered.recycle();try(OutputStream out=new FileOutputStream(cache)){bmp.compress(Bitmap.CompressFormat.JPEG,85,out);}}if(bmp==null)return;final Bitmap value=bmp;main.post(()->{if(dead){value.recycle();return;}Bitmap existing=coverCache.get(key);if(existing!=null){value.recycle();image.setImageBitmap(existing);}else{coverCache.put(key,value);image.setImageBitmap(value);}image.setPadding(0,0,0,0);image.setScaleType(ImageView.ScaleType.CENTER_CROP);});}catch(Exception|OutOfMemoryError ignored){}});
        }return image;
    }
    void showBook(Library.Book book){
        detail=book;base("detail");screen.addView(heading("漫画详情",()->{detail=null;showLibrary();}));ScrollView s=scroller(screen,true);LinearLayout body=column(this);pad(body,24,14);s.addView(body);LinearLayout hero=row(this);hero.setGravity(Gravity.TOP);hero.addView(cover(book,106,142),lp(this,106,142));LinearLayout words=column(this);pad(words,18,4);TextView name=text(this,book.title,23,INK,true);name.setMaxLines(3);words.addView(name);gap(words,12);label(words,book.chapters.size()+" 个章节  ·  "+book.totalPages()+" 页",12,MUTED,false);gap(words,18);words.addView(button(this,"自定义名称",false,()->rename(book)));hero.addView(words,new LinearLayout.LayoutParams(0,-2,1));body.addView(hero);gap(body,24);body.addView(button(this,book.touched==0?"开始阅读":"继续阅读 · 第 "+(book.page+1)+" 页",true,()->openReader(book,book.index(),book.page)),lp(this,-1,52));gap(body,28);LinearLayout chapterHead=row(this);chapterHead.addView(text(this,"全部章节",18,INK,true),new LinearLayout.LayoutParams(0,-2,1));chapterHead.addView(button(this,"调整顺序",false,()->reorder(book)));body.addView(chapterHead);gap(body,12);
        for(int i=0;i<book.chapters.size();i++){final int index=i;Library.Chapter c=book.chapters.get(i);LinearLayout r=row(this);pad(r,12,14);ripple(r,i==book.index()&&book.touched>0?SOFT:BG,14);TextView num=text(this,String.format(Locale.ROOT,"%02d",i+1),13,MUTED,false);r.addView(num,lp(this,40,40));LinearLayout tx=column(this);TextView n=text(this,c.name,14,INK,true);n.setMaxLines(2);n.setEllipsize(TextUtils.TruncateAt.END);tx.addView(n);gap(tx,6);Double number=ChapterOrder.number(c.name);label(tx,c.pages+" 页"+(number==null?"":"  ·  识别为第 "+format(number)+" 章"),11,MUTED,false);r.addView(tx,new LinearLayout.LayoutParams(0,-2,1));r.addView(new Icon(this,"right",MUTED),lp(this,24,24));r.setOnClickListener(v->openReader(book,index,0));body.addView(r);gap(body,4);}gap(body,24);
    }
    String format(double n){return n==(long)n?Long.toString((long)n):Double.toString(n);}
    void bookActions(Library.Book book){Dialog d=sheet(book.title);LinearLayout b=(LinearLayout)d.findViewById(1001);sheetAction(b,"继续阅读","回到上次翻阅的位置",()->{d.dismiss();openReader(book,book.index(),book.page);});sheetAction(b,"章节目录","查看与选择 PDF 章节",()->{d.dismiss();showBook(book);});sheetAction(b,"自定义名称","原始文件夹名称会保留",()->{d.dismiss();rename(book);});sheetAction(b,"更新章节","重新扫描这本漫画的原始文件夹",()->{d.dismiss();startImport(Uri.parse(book.source),false);});sheetAction(b,"移除漫画","仅清理应用内副本，原文件夹保留",()->{d.dismiss();new AlertDialog.Builder(this).setTitle("移除「"+book.title+"」？").setMessage("本应用中的阅读进度和导入副本将被移除，原始漫画文件夹会保留。").setNegativeButton("取消",null).setPositiveButton("移除",(dialog,w)->{try{library.remove(book);showLibrary();}catch(Exception e){error("移除失败",e);}}).show();});d.show();}
    void rename(Library.Book book){EditText edit=new EditText(this);edit.setText(book.title);edit.setSingleLine(true);edit.setSelectAllOnFocus(true);edit.setFilters(new InputFilter[]{new InputFilter.LengthFilter(100)});pad(edit,24,16);AlertDialog dialog=new AlertDialog.Builder(this).setTitle("漫画名称").setView(edit).setNegativeButton("取消",null).setPositiveButton("保存",null).create();dialog.setOnShowListener(d->{dialog.getButton(-1).setOnClickListener(v->{String value=edit.getText().toString().trim();if(value.isEmpty()){edit.setError("请输入名称");return;}String old=book.title;book.title=value;try{library.save();dialog.dismiss();if(location.equals("detail"))showBook(book);else showLibrary();}catch(Exception e){book.title=old;error("保存失败",e);}});edit.requestFocus();dialog.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);});dialog.show();}
    void reorder(Library.Book book){
        Dialog d=sheet("调整章节顺序");LinearLayout b=(LinearLayout)d.findViewById(1001);ArrayList<Library.Chapter> order=new ArrayList<>(book.chapters);LinearLayout list=column(this);Runnable[] fill=new Runnable[1];fill[0]=()->{list.removeAllViews();for(int i=0;i<order.size();i++){int pos=i;LinearLayout r=row(this);TextView name=text(this,(i+1)+". "+order.get(i).name,13,INK,false);name.setMaxLines(2);r.addView(name,new LinearLayout.LayoutParams(0,dp(this,56),1));TextView up=button(this,"↑",false,()->{if(pos>0){Collections.swap(order,pos,pos-1);fill[0].run();}}),down=button(this,"↓",false,()->{if(pos<order.size()-1){Collections.swap(order,pos,pos+1);fill[0].run();}});r.addView(up,lp(this,48,44));r.addView(down,lp(this,48,44));list.addView(r);gap(list,4);}};sheetAction(b,"按识别结果排序","支持中文章号、数字与番外",()->{order.sort((a,c)->ChapterOrder.compare(a.name,c.name));fill[0].run();});b.addView(list);fill[0].run();gap(b,14);b.addView(button(this,"保存顺序",true,()->{List<Library.Chapter> old=book.chapters;book.chapters=order;try{library.save();d.dismiss();showBook(book);}catch(Exception e){book.chapters=old;error("保存失败",e);}}),lp(this,-1,50));d.show();
    }
    Dialog sheet(String title){
        Dialog d=new Dialog(this);LinearLayout shell=column(this);surface(shell,BG,28);pad(shell,24,14);View handle=new View(this);surface(handle,LINE,3);LinearLayout.LayoutParams hp=lp(this,36,4);hp.gravity=Gravity.CENTER;shell.addView(handle,hp);gap(shell,14);LinearLayout header=row(this);header.addView(text(this,title,20,INK,true),new LinearLayout.LayoutParams(0,dp(this,48),1));header.addView(iconButton(this,"close","关闭",d::dismiss),lp(this,48,48));shell.addView(header);ScrollView scroll=new ScrollView(this);scroll.setVerticalScrollBarEnabled(false);LinearLayout body=column(this);body.setId(1001);gap(body,8);scroll.addView(body);shell.addView(scroll,new LinearLayout.LayoutParams(-1,-2));gap(shell,12);d.setContentView(shell);Window w=d.getWindow();if(w!=null){w.setBackgroundDrawable(new ColorDrawable(Color.TRANSPARENT));w.addFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND);WindowManager.LayoutParams p=w.getAttributes();p.gravity=Gravity.BOTTOM;p.width=-1;p.height=-2;p.dimAmount=.28f;w.setAttributes(p);}d.setOnShowListener(v->{int max=(int)(getResources().getDisplayMetrics().heightPixels*.82);shell.measure(View.MeasureSpec.makeMeasureSpec(getResources().getDisplayMetrics().widthPixels,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(max,View.MeasureSpec.AT_MOST));if(shell.getMeasuredHeight()>=max)d.getWindow().setLayout(-1,max);});return d;
    }
    void sheetAction(LinearLayout body,String title,String subtitle,Runnable action){LinearLayout r=row(this);pad(r,14,14);ripple(r,Color.TRANSPARENT,16);LinearLayout t=column(this);label(t,title,15,INK,true);if(subtitle!=null){gap(t,7);TextView help=text(this,subtitle,12,MUTED,false);help.setLineSpacing(dp(this,3),1);t.addView(help);}r.addView(t,new LinearLayout.LayoutParams(0,-2,1));r.addView(new Icon(this,"right",MUTED),lp(this,24,24));body.addView(r,lp(this,-1,-2));gap(body,4);r.setOnClickListener(v->action.run());}

    void pickFolder(boolean rootFolder){
        if(busy)return;Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION|Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);
        try{startActivityForResult(intent,rootFolder?42:41);}catch(ActivityNotFoundException e){error("未找到系统文件管理器",e);}
    }
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){super.onActivityResult(requestCode,resultCode,data);if((requestCode==41||requestCode==42)&&resultCode==RESULT_OK&&data!=null&&data.getData()!=null){Uri tree=data.getData();try{getContentResolver().takePersistableUriPermission(tree,data.getFlags()&Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(SecurityException e){error("无法保留文件夹访问权限",e);return;}if(requestCode==42)prefs.edit().putString("root",tree.toString()).apply();startImport(tree,requestCode==42);}}
    void scanRoot(){String path=prefs.getString("root","");if(path.isEmpty()){new AlertDialog.Builder(this).setTitle("设置书库根目录").setMessage("选择一个总文件夹，例如 Documents/墨间。以后把每本漫画文件夹放进去，点书架右上角刷新就能导入。\n\n每本漫画文件夹内放各章节 PDF。").setNegativeButton("取消",null).setPositiveButton("选择总文件夹",(d,w)->pickFolder(true)).show();}else startImport(Uri.parse(path),true);}
    void startImport(Uri uri,boolean rootFolder){
        if(busy)return;busy=true;cancelImport=false;busyDialog=sheet(rootFolder?"扫描书库":"导入漫画");LinearLayout body=(LinearLayout)busyDialog.findViewById(1001);ProgressBar spinner=new ProgressBar(this);body.addView(spinner,lp(this,-1,38));gap(body,18);importMessage=text(this,"正在读取文件夹…",14,INK,false);importMessage.setGravity(Gravity.CENTER);body.addView(importMessage,lp(this,-1,70));gap(body,18);body.addView(button(this,"取消导入",false,()->{cancelImport=true;importMessage.setText("正在取消…");}));busyDialog.setCancelable(false);busyDialog.show();
        View close=busyDialog.getWindow().getDecorView().findViewWithTag("icon-close");
        if(close!=null)close.setOnClickListener(v->{cancelImport=true;importMessage.setText("正在取消…");});
        Library.Progress progress=new Library.Progress(){public void update(String message){main.post(()->{if(!dead&&busy)importMessage.setText(message);});}public boolean cancelled(){return cancelImport||dead;}};
        importer.submit(()->{
            ArrayList<String> errors=new ArrayList<>();int count=0;
            try{
                Uri folder=DocumentsUri(uri);ArrayList<Uri> targets=new ArrayList<>();
                if(rootFolder){for(Library.Doc child:library.children(folder))if(child.directory)targets.add(child.uri);if(targets.isEmpty())throw new IOException("总文件夹中没有漫画子文件夹。请选择包含「漫画名/章节.pdf」的总目录。");}else targets.add(folder);
                for(Uri target:targets){Library.check(progress);Library.Book existing=library.findSource(target.toString());Library.Book result=null;
                    try{result=library.importFolder(target,existing,progress);Library.check(progress);final Library.Book completed=result;CountDownLatch latch=new CountDownLatch(1);Exception[] failure={null};main.post(()->{try{if(dead||cancelImport)library.discard(completed);else library.commit(completed);}catch(Exception e){failure[0]=e;}finally{latch.countDown();}});latch.await();if(failure[0]!=null)throw failure[0];if(!cancelImport)count++;}
                    catch(InterruptedIOException e){if(result!=null)library.discard(result);throw e;}
                    catch(Exception e){errors.add(e.getMessage());if(!rootFolder)break;}
                }
            }catch(InterruptedIOException|InterruptedException e){errors.add("导入已取消，已经完成的漫画会保留");}catch(Exception e){errors.add("无法读取文件夹，请重新选择授权。\n"+e.getMessage());}
            final int added=count;main.post(()->{if(dead)return;busy=false;busyDialog.dismiss();showLibrary();if(errors.isEmpty())toast("已导入 "+added+" 本漫画");else new AlertDialog.Builder(this).setTitle(added>0?"已完成 "+added+" 本漫画":"导入提示").setMessage(TextUtils.join("\n\n",errors)).setPositiveButton("知道了",null).show();});
        });
    }
    Uri DocumentsUri(Uri uri){return "tree".equals(uri.getPathSegments().get(0))&&uri.getPathSegments().size()==2?library.document(uri):uri;}

    boolean dual(){String mode=prefs.getString("layout","auto");return mode.equals("dual")||(mode.equals("auto")&&getResources().getConfiguration().orientation==Configuration.ORIENTATION_LANDSCAPE);}
    boolean webtoon(){return prefs.getString("layout","auto").equals("webtoon");}
    int turnDirection(int physical){return !webtoon()&&prefs.getBoolean("rtl",false)?-physical:physical;}
    void disposeReaderViews(){
        if(chromeMotion!=null){chromeMotion.dispose();chromeMotion=null;}
        if(renderJob!=null){renderJob.cancel(true);renderJob=null;}
        if(webtoonView!=null){webtoonView.dispose();webtoonView=null;}
        if(pageView!=null){pageView.dispose();pageView=null;}
        main.removeCallbacks(saveWebtoon);
    }
    void openReader(Library.Book book,int index,int target){
        if(book.chapters.isEmpty())return;disposeReaderViews();active=book;chapterIndex=Math.max(0,Math.min(index,book.chapters.size()-1));page=target;detail=null;request++;base("reader");screen.setBackgroundColor(0xffeef1e9);chrome=true;
        readerHeader=row(this);pad(readerHeader,8,6);readerHeader.setBackgroundColor(BG);readerHeader.addView(iconButton(this,"back","返回书架",this::closeReader),lp(this,48,48));LinearLayout names=column(this);readerTitle=text(this,book.title,14,INK,true);readerTitle.setSingleLine(true);readerTitle.setEllipsize(TextUtils.TruncateAt.END);names.addView(readerTitle);gap(names,5);readerChapterLabel=text(this,book.chapters.get(chapterIndex).name,11,MUTED,false);readerChapterLabel.setSingleLine(true);readerChapterLabel.setEllipsize(TextUtils.TruncateAt.END);names.addView(readerChapterLabel);readerHeader.addView(names,new LinearLayout.LayoutParams(0,-2,1));readerHeader.addView(iconButton(this,"chapters","章节目录",this::readerChapters),lp(this,48,48));readerHeader.addView(iconButton(this,"settings","阅读设置",this::readerOptions),lp(this,48,48));headerSlot=ReaderChromeMotion.wrap(screen,readerHeader);
        FrameLayout stage=new FrameLayout(this);readerStage=stage;pageView=new PageView(this,new PageView.Actions(){public void turn(int physical){step(turnDirection(physical));}public void toggleChrome(){toggleTools();}});pageView.fitWidth=prefs.getString("fit","page").equals("width");stage.addView(pageView,new FrameLayout.LayoutParams(-1,-1));loading=text(this,"正在展开故事…",13,MUTED,false);loading.setGravity(Gravity.CENTER);FrameLayout.LayoutParams loadp=new FrameLayout.LayoutParams(-1,dp(this,42),Gravity.CENTER);stage.addView(loading,loadp);screen.addView(stage,new LinearLayout.LayoutParams(-1,0,1));
        readerFooter=column(this);readerFooter.setBackgroundColor(BG);pad(readerFooter,16,4);seek=new SeekBar(this);seek.setPadding(dp(this,10),0,dp(this,10),0);seek.setProgressTintList(android.content.res.ColorStateList.valueOf(GREEN));seek.setThumbTintList(android.content.res.ColorStateList.valueOf(GREEN));readerFooter.addView(seek,lp(this,-1,32));seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onStartTrackingTouch(SeekBar s){}public void onProgressChanged(SeekBar s,int p,boolean user){if(user)pageLabel.setText("第 "+(p+1)+" 页");}public void onStopTrackingTouch(SeekBar s){page=s.getProgress();renderPage(0,true);}});
        LinearLayout controls=row(this);controls.addView(iconButton(this,"left","上一页",()->step(turnDirection(-1))),lp(this,48,44));pageLabel=text(this,"—",12,INK,true);pageLabel.setGravity(Gravity.CENTER);pageLabel.setOnClickListener(v->jump());controls.addView(pageLabel,new LinearLayout.LayoutParams(0,dp(this,44),1));controls.addView(iconButton(this,"right","下一页",()->step(turnDirection(1))),lp(this,48,44));readerFooter.addView(controls);footerSlot=ReaderChromeMotion.wrap(screen,readerFooter);
        if(webtoon()){
            stage.removeView(pageView);pageView.dispose();pageView=null;
            double fraction=book.chapter.equals(book.chapters.get(chapterIndex).path)&&book.page==target?book.scrollFraction:0;
            webtoonView=new WebtoonView(this,library,book,chapterIndex,target,fraction,new WebtoonView.Listener(){
                public void ready(){if(active==book&&!dead)loading.setVisibility(View.GONE);}
                public void error(String message){if(active==book&&!dead)loading.setText(message);}
                public void toggleTools(){MainActivity.this.toggleTools();}
                public void position(int chapter,int number,double offset,boolean end){
                    if(dead||active!=book)return;chapterIndex=chapter;page=number;
                    Library.Chapter selected=book.chapters.get(chapter);book.chapter=selected.path;book.page=number;book.scrollFraction=offset;book.touched=System.currentTimeMillis();
                    book.scrollMode=true;book.scrollFinished=end;
                    seek.setMax(selected.pages-1);seek.setProgress(number);pageLabel.setText((number+1)+" / "+selected.pages+" · 条漫");readerChapterLabel.setText(selected.name);
                    main.removeCallbacks(saveWebtoon);main.postDelayed(saveWebtoon,450);
                }
            });stage.addView(webtoonView,0,new FrameLayout.LayoutParams(-1,-1));
        }else pageView.post(()->renderPage(0,false));
        fitReaderControls();chromeMotion=new ReaderChromeMotion(headerSlot,readerHeader,footerSlot,readerFooter,this::readerSystemBars);readerSystemBars(true);getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }
    void fitReaderControls(){if(readerFooter==null||seek==null)return;boolean wide=getResources().getConfiguration().orientation==Configuration.ORIENTATION_LANDSCAPE;readerFooter.setOrientation(wide?LinearLayout.HORIZONTAL:LinearLayout.VERTICAL);readerFooter.setGravity(Gravity.CENTER_VERTICAL);seek.setLayoutParams(new LinearLayout.LayoutParams(wide?0:-1,dp(this,wide?44:32),wide?1:0));readerFooter.getChildAt(1).setLayoutParams(lp(this,wide?184:-1,44));if(chromeMotion!=null)chromeMotion.reflow();}
    void renderPage(int direction,boolean animate){
        if(webtoonView!=null){webtoonView.jumpTo(chapterIndex,page,0);return;}
        if(active==null||pageView==null||dead)return;int token=++request;Library.Book book=active;Library.Chapter chapter=book.chapters.get(chapterIndex);int target=page;boolean two=dual(),rtl=prefs.getBoolean("rtl",false);PageView view=pageView;int width=Math.max(view.getWidth(),dp(this,320)),height=Math.max(view.getHeight(),dp(this,300));
        if(renderJob!=null)renderJob.cancel(true);loading.setText("正在加载…");loading.setVisibility(View.VISIBLE);
        renderJob=renderer.submit(()->{try{PdfEngine.Spread spread=PdfEngine.render(library.file(chapter),target,two,rtl,width,height);main.post(()->{if(dead||token!=request||active!=book||pageView!=view){spread.bitmap.recycle();return;}loading.setVisibility(View.GONE);page=spread.first;view.fitWidth=prefs.getString("fit","page").equals("width");view.setBitmap(spread.bitmap,direction,prefs.getInt("effect",0),animate&&prefs.getBoolean("motion",true));seek.setMax(spread.total-1);seek.setProgress(page);pageLabel.setText((spread.first==spread.last?Integer.toString(page+1):(page+1)+"–"+(spread.last+1))+" / "+spread.total);book.chapter=chapter.path;book.page=spread.last;book.scrollFraction=0;book.scrollMode=false;book.scrollFinished=false;book.touched=System.currentTimeMillis();persist();readerChapterLabel.setText(chapter.name);});}
            catch(Exception|OutOfMemoryError e){main.post(()->{if(!dead&&token==request){loading.setText("页面暂时无法打开\n请返回后重试，或重新导入此章节");toast(e instanceof OutOfMemoryError?"页面较大，设备内存不足":"无法读取 PDF："+e.getMessage());}});}});
    }
    void step(int delta){
        if(active==null)return;Library.Chapter current=active.chapters.get(chapterIndex);int next=ChapterOrder.start(page,current.pages,dual())+(dual()?2:1)*delta;
        if(next>=current.pages){if(chapterIndex+1>=active.chapters.size()){toast("这本漫画已经读完了");return;}chapterIndex++;page=0;}
        else if(next<0){if(chapterIndex==0){toast("已经是第一页");return;}chapterIndex--;page=active.chapters.get(chapterIndex).pages-1;}else page=next;
        renderPage(delta,true);
    }
    void toggleTools(){
        if(chromeMotion==null||active==null)return;
        chrome=!chrome;chromeMotion.setVisible(chrome,prefs.getBoolean("motion",true));
    }
    void readerSystemBars(boolean show){
        if(dead||active==null||!location.equals("reader"))return;
        getWindow().getDecorView().setSystemUiVisibility(show?View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR:View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
    }
    void closeReader(){request++;disposeReaderViews();persist();active=null;getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);showLibrary();}
    void readerChapters(){if(active==null)return;Dialog d=sheet("章节目录");LinearLayout body=(LinearLayout)d.findViewById(1001);for(int i=0;i<active.chapters.size();i++){int index=i;Library.Chapter c=active.chapters.get(i);sheetAction(body,(i==chapterIndex?"正在阅读 · ":"")+c.name,c.pages+" 页",()->{d.dismiss();chapterIndex=index;page=0;renderPage(1,true);});}d.show();}
    void jump(){if(active==null)return;EditText edit=new EditText(this);edit.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);edit.setSingleLine(true);edit.setText(Integer.toString(page+1));edit.selectAll();pad(edit,24,16);int count=active.chapters.get(chapterIndex).pages;AlertDialog d=new AlertDialog.Builder(this).setTitle("跳转页码 · 共 "+count+" 页").setView(edit).setNegativeButton("取消",null).setPositiveButton("跳转",null).create();d.setOnShowListener(x->d.getButton(-1).setOnClickListener(v->{try{int p=Integer.parseInt(edit.getText().toString());if(p<1||p>count)throw new NumberFormatException();page=p-1;d.dismiss();renderPage(0,true);}catch(NumberFormatException e){edit.setError("请输入 1 到 "+count);}}));d.show();}
    void choices(String title,String[] labels,String[] descriptions,int selected,java.util.function.IntConsumer choose){Dialog d=sheet(title);LinearLayout body=(LinearLayout)d.findViewById(1001);for(int i=0;i<labels.length;i++){int index=i;LinearLayout r=row(this);pad(r,14,14);ripple(r,i==selected?SOFT:BG,16);LinearLayout tx=column(this);label(tx,labels[i],15,i==selected?GREEN:INK,true);gap(tx,7);label(tx,descriptions[i],12,MUTED,false);r.addView(tx,new LinearLayout.LayoutParams(0,-2,1));if(i==selected)r.addView(new Icon(this,"check",GREEN),lp(this,24,24));r.setOnClickListener(v->{d.dismiss();choose.accept(index);});body.addView(r);gap(body,8);}d.show();}
    String layoutName(){String mode=prefs.getString("layout","auto");return mode.equals("webtoon")?"条漫模式":mode.equals("auto")?"随屏幕旋转":mode.equals("dual")?"双页展开":"单页阅读";}
    void setReaderLayout(String mode){
        if(webtoonView!=null)webtoonView.flushPosition();
        prefs.edit().putString("layout",mode).apply();
        if(active!=null){Library.Book book=active;int chapter=chapterIndex,number=page;openReader(book,chapter,number);}
        else showSettings();
    }
    void chooseLayout(){String[] values={"auto","single","dual","webtoon"};choices("页面布局",new String[]{"随屏幕旋转","单页阅读","双页展开","条漫模式"},new String[]{"竖屏单页，横屏并排两页","适合手机竖屏与放大阅读","真实相邻两页，奇数末页居中","适合宽度，上下连续滚动，可跨章阅读"},Arrays.asList(values).indexOf(prefs.getString("layout","auto")),i->setReaderLayout(values[i]));}
    void chooseFit(){choices("页面缩放",new String[]{"完整页面","适合宽度"},new String[]{"在屏幕内显示整页内容","铺满可用宽度，可上下拖动"},prefs.getString("fit","page").equals("width")?1:0,i->{prefs.edit().putString("fit",i==0?"page":"width").apply();if(pageView!=null){pageView.fitWidth=i==1;pageView.zoom=1;pageView.offsetX=pageView.offsetY=0;pageView.clamp();pageView.invalidate();}else showSettings();});}
    void chooseEffect(){choices("翻页动画",new String[]{"轻滑","淡入","舒展","直接切换"},new String[]{"页面沿翻阅方向滑入","柔和淡入新的一页","轻微缩放，让画面展开","立即显示，减少动态效果"},prefs.getInt("effect",0),i->{prefs.edit().putInt("effect",i).apply();if(active==null)showSettings();});}
    void readerOptions(){
        Dialog d=sheet("阅读设置");LinearLayout b=(LinearLayout)d.findViewById(1001);
        sheetAction(b,"页面布局",layoutName(),()->{d.dismiss();chooseLayout();});
        if(webtoon()){
            sheetAction(b,"重置缩放","恢复适合宽度，继续上下阅读",()->{d.dismiss();if(webtoonView!=null)webtoonView.setZoom(1,webtoonView.getWidth()/2f,0);});
        }else{
            sheetAction(b,"页面缩放",prefs.getString("fit","page").equals("width")?"适合宽度":"完整页面",()->{d.dismiss();chooseFit();});
            sheetAction(b,"阅读方向",prefs.getBoolean("rtl",false)?"从右向左":"从左向右",()->{d.dismiss();chooseDirection();});
            sheetAction(b,"翻页动画",new String[]{"轻滑","淡入","舒展","直接切换"}[prefs.getInt("effect",0)],()->{d.dismiss();chooseEffect();});
        }
        TextView help=text(this,webtoon()?"上下滑动连续阅读 · 自动衔接下一章\n双指缩放 · 双击放大 · 轻点显示工具栏":"左右滑动翻页 · 双指缩放\n双击切换放大 · 轻点中央隐藏工具栏",12,MUTED,false);
        help.setLineSpacing(dp(this,7),1);pad(help,14,18);b.addView(help);d.show();
    }
    void chooseDirection(){choices("阅读方向",new String[]{"从左向右","从右向左"},new String[]{"向左滑动翻到下一页","向右滑动翻到下一页；双页反向排列"},prefs.getBoolean("rtl",false)?1:0,i->{prefs.edit().putBoolean("rtl",i==1).apply();if(active!=null)renderPage(0,false);else showSettings();});}
    void showSettings(){
        base("settings");screen.addView(heading("偏好设置",null));ScrollView scroll=scroller(screen,true);LinearLayout body=column(this);pad(body,24,12);scroll.addView(body);label(body,"按你的习惯，安静阅读",13,MUTED,false);gap(body,28);label(body,"阅读体验",12,GREEN,true);gap(body,10);LinearLayout card=column(this);surface(card,Color.WHITE,22);pad(card,4,6);sheetAction(card,"页面布局",layoutName(),this::chooseLayout);sheetAction(card,"页面缩放",prefs.getString("fit","page").equals("width")?"适合宽度":"完整页面",this::chooseFit);sheetAction(card,"阅读方向",prefs.getBoolean("rtl",false)?"从右向左":"从左向右",this::chooseDirection);sheetAction(card,"翻页动画",new String[]{"轻滑","淡入","舒展","直接切换"}[prefs.getInt("effect",0)],this::chooseEffect);
        LinearLayout motion=row(this);pad(motion,14,14);LinearLayout words=column(this);label(words,"界面动画",15,INK,true);gap(words,7);label(words,"书架、详情和阅读间的过渡",12,MUTED,false);motion.addView(words,new LinearLayout.LayoutParams(0,-2,1));Switch toggle=new Switch(this);toggle.setContentDescription("界面动画");toggle.setChecked(prefs.getBoolean("motion",true));toggle.setOnCheckedChangeListener((b,checked)->prefs.edit().putBoolean("motion",checked).apply());motion.addView(toggle);card.addView(motion);body.addView(card);gap(body,28);label(body,"书库与文件夹",12,GREEN,true);gap(body,10);LinearLayout files=column(this);surface(files,Color.WHITE,22);pad(files,4,6);sheetAction(files,"导入一本漫画","选择含章节 PDF 的漫画文件夹",()->pickFolder(false));sheetAction(files,"书库根目录",prefs.getString("root","").isEmpty()?"未设置 · 支持批量扫描漫画子文件夹":"已设置 · 点此重新选择",()->pickFolder(true));sheetAction(files,"扫描根目录","添加新漫画，更新已有章节",this::scanRoot);body.addView(files);gap(body,24);TextView help=text(this,"文件夹名会作为默认漫画名，可在漫画详情中修改。导入会复制 PDF 到应用内；清除应用数据或卸载会移除应用副本与进度，请保留原始漫画文件。\n\n双页直接并排显示，无书脊、页间阴影和纸张边缘。",12,MUTED,false);help.setLineSpacing(dp(this,5),1);body.addView(help);gap(body,24);sheetAction(body,"关于墨间","Android 1.1.1 · 离线阅读 · 无广告",()->new AlertDialog.Builder(this).setTitle("墨间 · Android 1.1.1").setMessage("让故事，慢慢展开。\n\n完全本地的 PDF 漫画阅读器。使用 Android 系统 PDF 引擎，无需联网。\n\n本安卓工程按 AGPL-3.0 发布，源代码随安装包提供。\nhttps://www.gnu.org/licenses/agpl-3.0.html").setPositiveButton("知道了",null).show());gap(body,20);bottom(screen,"偏好");
    }
}
