package com.mangashelf.mojian;

import android.content.*;
import android.database.Cursor;
import android.graphics.pdf.PdfRenderer;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.DocumentsContract;
import android.util.AtomicFile;
import org.json.*;
import java.io.*;
import java.util.*;

final class Library {
    static class Chapter {
        String name, path, source; int pages; long bytes, modified;
        JSONObject json() throws JSONException {
            return new JSONObject().put("name",name).put("path",path).put("source",source).put("pages",pages).put("bytes",bytes).put("modified",modified);
        }
        static Chapter from(JSONObject j) throws JSONException {
            Chapter c=new Chapter(); c.name=j.getString("name");c.path=j.getString("path");c.source=j.optString("source");c.pages=j.getInt("pages");c.bytes=j.optLong("bytes");c.modified=j.optLong("modified");return c;
        }
    }
    static class Book {
        String id=UUID.randomUUID().toString(), title, folder, source, chapter="";
        int page=0; double scrollFraction=0; long touched=0; List<Chapter> chapters=new ArrayList<>();
        boolean scrollMode=false, scrollFinished=false;
        JSONObject json() throws JSONException {
            JSONArray cs=new JSONArray(); for(Chapter c:chapters)cs.put(c.json());
            return new JSONObject().put("id",id).put("title",title).put("folder",folder).put("source",source).put("chapter",chapter).put("page",page).put("scrollFraction",scrollFraction).put("scrollMode",scrollMode).put("scrollFinished",scrollFinished).put("touched",touched).put("chapters",cs);
        }
        static Book from(JSONObject j) throws JSONException {
            Book b=new Book();b.id=j.getString("id");b.title=j.getString("title");b.folder=j.getString("folder");b.source=j.optString("source");b.chapter=j.optString("chapter");b.page=j.optInt("page");b.scrollFraction=Math.max(0,Math.min(.999999,j.optDouble("scrollFraction",0)));b.touched=j.optLong("touched");
            b.scrollMode=j.optBoolean("scrollMode",false);b.scrollFinished=j.optBoolean("scrollFinished",false);
            JSONArray cs=j.getJSONArray("chapters");for(int i=0;i<cs.length();i++)b.chapters.add(Chapter.from(cs.getJSONObject(i)));return b;
        }
        int index() { for(int i=0;i<chapters.size();i++)if(chapters.get(i).path.equals(chapter))return i;return 0; }
        int totalPages(){int n=0;for(Chapter c:chapters)n+=c.pages;return n;}
        float progress(){int n=0;int index=index();for(int i=0;i<index;i++)n+=chapters.get(i).pages;return touched==0?0:scrollMode&&scrollFinished?1:Math.min(1f,(float)(n+page+(scrollMode?scrollFraction:1))/Math.max(1,totalPages()));}
    }
    static class Doc {
        Uri uri; String name,relative; boolean directory;long bytes, modified;
    }
    interface Progress { void update(String message); boolean cancelled(); }
    final Context context; final File booksDir; final AtomicFile store; final List<Book> books=new ArrayList<>();
    Library(Context context) throws Exception {
        this.context=context;
        File external=context.getExternalFilesDir(null);
        booksDir=new File(external==null?context.getFilesDir():external,"comics");
        if(!booksDir.exists()&&!booksDir.mkdirs())throw new IOException("无法创建漫画目录");
        store=new AtomicFile(new File(context.getFilesDir(),"library.json"));
        if(store.getBaseFile().exists()||new File(store.getBaseFile()+".bak").exists()) {
            try(InputStream in=store.openRead()) { JSONArray arr=new JSONObject(new String(read(in),"UTF-8")).getJSONArray("books");for(int i=0;i<arr.length();i++)books.add(Book.from(arr.getJSONObject(i))); }
        }
    }
    void save() throws Exception {
        JSONArray arr=new JSONArray();for(Book b:books)arr.put(b.json());
        byte[] data=new JSONObject().put("version",1).put("books",arr).toString().getBytes("UTF-8");
        FileOutputStream out=null;
        try {out=store.startWrite();out.write(data);store.finishWrite(out);}catch(Exception e){store.failWrite(out);throw e;}
    }
    File file(Chapter c) throws IOException {
        File f=new File(booksDir,c.path).getCanonicalFile();
        if(!f.toPath().startsWith(booksDir.getCanonicalFile().toPath()))throw new IOException("无效漫画路径");return f;
    }
    List<Doc> children(Uri folder) throws Exception {
        String id=DocumentsContract.getDocumentId(folder);
        Uri list=DocumentsContract.buildChildDocumentsUriUsingTree(folder,id);List<Doc> docs=new ArrayList<>();
        String[] projection={DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE,DocumentsContract.Document.COLUMN_SIZE,DocumentsContract.Document.COLUMN_LAST_MODIFIED};
        try(Cursor c=context.getContentResolver().query(list,projection,null,null,null)) {
            if(c==null)throw new IOException("无法读取所选文件夹");
            while(c.moveToNext()){Doc d=new Doc();d.uri=DocumentsContract.buildDocumentUriUsingTree(folder,c.getString(0));d.name=c.getString(1);d.directory=DocumentsContract.Document.MIME_TYPE_DIR.equals(c.getString(2));d.bytes=c.getLong(3);d.modified=c.getLong(4);docs.add(d);}
        }
        docs.sort((a,b)->ChapterOrder.natural(a.name,b.name));return docs;
    }
    Uri document(Uri tree) {return DocumentsContract.buildDocumentUriUsingTree(tree,DocumentsContract.getTreeDocumentId(tree));}
    String name(Uri folder) throws Exception {
        try(Cursor c=context.getContentResolver().query(folder,new String[]{DocumentsContract.Document.COLUMN_DISPLAY_NAME},null,null,null)){if(c!=null&&c.moveToFirst())return c.getString(0);}throw new IOException("无法读取文件夹名称");
    }
    void collect(Uri folder,String prefix,List<Doc> result,Progress progress,int depth) throws Exception {
        if(depth>24)throw new IOException("文件夹层级太深，请选择漫画所在文件夹");
        for(Doc d:children(folder)) {
            check(progress);d.relative=prefix+d.name;
            if(d.directory)collect(d.uri,d.relative+"/",result,progress,depth+1);
            else if(d.name.toLowerCase(Locale.ROOT).endsWith(".pdf"))result.add(d);
        }
    }
    Book importFolder(Uri folder,Book existing,Progress progress) throws Exception {
        List<Doc> docs=new ArrayList<>();collect(folder,"",docs,progress,0);
        if(docs.isEmpty())throw new IOException("文件夹里没有 PDF 章节");
        docs.sort((a,b)->{int c=ChapterOrder.compare(a.name,b.name);return c==0?ChapterOrder.natural(a.relative,b.relative):c;});
        Book result=new Book();result.source=folder.toString();result.folder=name(folder);result.title=existing==null?result.folder:existing.title;
        if(existing!=null){result.id=existing.id;result.chapter=existing.chapter;result.page=existing.page;result.scrollFraction=existing.scrollFraction;result.touched=existing.touched;}
        if(existing!=null){result.scrollMode=existing.scrollMode;result.scrollFinished=existing.scrollFinished;}
        File stage=new File(booksDir,".incoming-"+UUID.randomUUID());
        if(!stage.mkdirs())throw new IOException("无法创建导入目录");
        // Each import writes a complete new generation. Only the atomic JSON commit makes it live.
        String generation=result.id+"-"+UUID.randomUUID(); File finalDir=new File(booksDir,generation);
        try {
            for(int i=0;i<docs.size();i++) {
                check(progress);Doc d=docs.get(i);progress.update("正在导入 "+(i+1)+" / "+docs.size()+"\n"+d.name);
                File destination=new File(stage,String.format(Locale.ROOT,"%05d.pdf",i));
                Chapter old=null;
                if(existing!=null)for(Chapter c:existing.chapters)if(c.source.equals(d.relative)){old=c;break;}
                boolean unchanged=old!=null&&d.modified>0&&old.modified==d.modified&&old.bytes==d.bytes&&file(old).isFile();
                try(InputStream in=unchanged?new FileInputStream(file(old)):context.getContentResolver().openInputStream(d.uri);OutputStream out=new FileOutputStream(destination)){
                    if(in==null)throw new IOException("无法读取 "+d.name);byte[] buf=new byte[262144];int n;
                    while((n=in.read(buf))!=-1){check(progress);out.write(buf,0,n);}
                }
                Chapter c=new Chapter();c.name=d.name.replaceFirst("(?i)\\.pdf$","");c.source=d.relative;c.bytes=d.bytes;c.modified=d.modified;
                try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(destination,ParcelFileDescriptor.MODE_READ_ONLY);PdfRenderer renderer=new PdfRenderer(fd)){c.pages=renderer.getPageCount();}
                catch(Exception e){throw new IOException(d.name+" 无法打开，可能已损坏或需要密码",e);}
                if(c.pages==0)throw new IOException(d.name+" 没有可阅读页面");
                c.path=generation+"/"+destination.getName();result.chapters.add(c);
                if(old!=null&&old.path.equals(result.chapter)){result.chapter=c.path;result.page=Math.min(result.page,c.pages-1);}
            }
            if(existing!=null&&result.totalPages()!=existing.totalPages())result.scrollFinished=false;
            check(progress);if(!stage.renameTo(finalDir))throw new IOException("保存漫画失败，请检查剩余空间");return result;
        } finally { deleteOwned(stage); }
    }
    void commit(Book book) throws Exception {
        int index=-1;Book previous=null;
        for(int i=0;i<books.size();i++)if(books.get(i).id.equals(book.id)){index=i;previous=books.get(i);break;}
        if(index<0)books.add(book);else books.set(index,book);
        try{save();}catch(Exception e){if(index<0)books.remove(book);else books.set(index,previous);discard(book);throw e;}
        if(previous!=null)try{discard(previous);}catch(IOException ignored){/* Committed data stays valid if old generation cleanup fails. */}
    }
    void discard(Book b) throws IOException {Set<String> dirs=new HashSet<>();for(Chapter c:b.chapters){File parent=file(c).getParentFile();if(parent!=null&&dirs.add(parent.getPath()))deleteOwned(parent);}}
    void remove(Book b) throws Exception {int index=books.indexOf(b);books.remove(b);try{save();}catch(Exception e){books.add(index,b);throw e;}discard(b);}
    void deleteOwned(File file) throws IOException {
        File f=file.getCanonicalFile(), root=booksDir.getCanonicalFile();
        if(f.equals(root)||!f.toPath().startsWith(root.toPath()))throw new IOException("无效目录");
        if(f.isDirectory()){File[] children=f.listFiles();if(children!=null)for(File c:children)deleteOwned(c);}
        if(f.exists()&&!f.delete())throw new IOException("无法清理临时文件");
    }
    static String sourceKey(String source){try{Uri uri=Uri.parse(source);return uri.getAuthority()+":"+DocumentsContract.getDocumentId(uri);}catch(Exception e){return source;}}
    Book findSource(String source){String key=sourceKey(source);for(Book b:books)if(key.equals(sourceKey(b.source)))return b;return null;}
    static void check(Progress p) throws InterruptedIOException {if(Thread.currentThread().isInterrupted()||p.cancelled())throw new InterruptedIOException("导入已取消");}
    static byte[] read(InputStream in)throws IOException{ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1)out.write(b,0,n);return out.toByteArray();}
}
