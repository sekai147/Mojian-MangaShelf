package com.mangashelf.mojian;

import android.database.*;
import android.graphics.*;
import android.graphics.pdf.PdfDocument;
import android.os.*;
import android.provider.DocumentsContract;
import android.provider.DocumentsProvider;
import java.io.*;
import java.util.*;

/** A separate test APK only: exercises real SAF streams without touching user files. */
public class FixtureProvider extends DocumentsProvider {
    File root;
    public boolean onCreate(){root=new File(getContext().getFilesDir(),"fixtures");root.mkdirs();try{root=root.getCanonicalFile();
        pdf("A/第十二话.pdf",2,Color.rgb(232,210,170));pdf("A/第2话.pdf",3,Color.rgb(80,160,190));pdf("A/嵌套/chapter 1.pdf",3,Color.rgb(170,195,160));pdf("A/番外.pdf",1,Color.rgb(190,155,190));pdf("B/Chapter 01.pdf",2,Color.rgb(210,170,130));
        new File(root,"Broken").mkdirs();try(OutputStream out=new FileOutputStream(new File(root,"Broken/01.pdf"))){out.write("not a PDF".getBytes());}
    }catch(Exception e){throw new RuntimeException(e);}return true;}
    void pdf(String name,int pages,int color)throws Exception{File f=new File(root,name);if(f.exists())return;f.getParentFile().mkdirs();PdfDocument document=new PdfDocument();try{
        for(int i=0;i<pages;i++){PdfDocument.Page page=document.startPage(new PdfDocument.PageInfo.Builder(400,600,i+1).create());Canvas canvas=page.getCanvas();canvas.drawColor(i%2==0?color:Color.rgb(235,220,197));Paint p=new Paint(3);p.setColor(Color.rgb(42,68,56));p.setTextSize(38);canvas.drawText("MOJIAN",36,70,p);p.setTextSize(18);canvas.drawText("CHAPTER / PAGE "+(i+1),36,102,p);
            p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3);canvas.drawRect(28,125,372,360,p);canvas.drawRect(28,375,195,555,p);canvas.drawRect(210,375,372,555,p);canvas.drawCircle(200,230,70,p);canvas.drawLine(130,300,270,160,p);canvas.drawLine(280,165,335,230,p);p.setTextSize(20);p.setStyle(Paint.Style.FILL);canvas.drawText("Quiet stories.",45,430,p);canvas.drawText("Keep reading.",220,525,p);document.finishPage(page);}
        try(OutputStream out=new FileOutputStream(f)){document.writeTo(out);}
    }finally{document.close();}}
    String[] cols(String[] p){return p!=null?p:new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE,DocumentsContract.Document.COLUMN_SIZE,DocumentsContract.Document.COLUMN_LAST_MODIFIED};}
    File file(String id)throws FileNotFoundException{try{File f=id.equals("root")?root:new File(root,id).getCanonicalFile();if(!f.toPath().startsWith(root.getCanonicalFile().toPath()))throw new FileNotFoundException();return f;}catch(IOException e){throw new FileNotFoundException();}}
    void add(MatrixCursor cursor,File f)throws Exception{String id=f.equals(root)?"root":root.toPath().relativize(f.toPath()).toString().replace('\\','/');String title=id.equals("A")?"森间来信":id.equals("B")?"山海片刻":f.getName();MatrixCursor.RowBuilder r=cursor.newRow();for(String col:cursor.getColumnNames()){Object v=null;if(col.equals(DocumentsContract.Document.COLUMN_DOCUMENT_ID))v=id;if(col.equals(DocumentsContract.Document.COLUMN_DISPLAY_NAME))v=title;if(col.equals(DocumentsContract.Document.COLUMN_MIME_TYPE))v=f.isDirectory()?DocumentsContract.Document.MIME_TYPE_DIR:"application/pdf";if(col.equals(DocumentsContract.Document.COLUMN_SIZE))v=f.length();if(col.equals(DocumentsContract.Document.COLUMN_LAST_MODIFIED))v=f.lastModified();r.add(v);}}
    public Cursor queryRoots(String[] p){return new MatrixCursor(p==null?new String[]{DocumentsContract.Root.COLUMN_ROOT_ID}:p);}
    public Cursor queryDocument(String id,String[] p)throws FileNotFoundException{MatrixCursor c=new MatrixCursor(cols(p));try{add(c,file(id));}catch(Exception e){throw new FileNotFoundException(e.getMessage());}return c;}
    public Cursor queryChildDocuments(String id,String[] p,String sort)throws FileNotFoundException{MatrixCursor c=new MatrixCursor(cols(p));File[] fs=file(id).listFiles();if(fs==null)throw new FileNotFoundException(id);try{for(File f:fs)add(c,f);}catch(Exception e){throw new FileNotFoundException(e.getMessage());}return c;}
    public ParcelFileDescriptor openDocument(String id,String mode,CancellationSignal signal)throws FileNotFoundException{return ParcelFileDescriptor.open(file(id),ParcelFileDescriptor.MODE_READ_ONLY);}
    public boolean isChildDocument(String parent,String document){return parent.equals("root")||document.startsWith(parent+"/");}
    public Bundle call(String method,String arg,Bundle extras){Bundle b=new Bundle();try{if(method.equals("append")){pdf("A/第3话.pdf",2,Color.rgb(185,160,140));b.putBoolean("ok",true);return b;}if(method.equals("addBook")){pdf("C/01.pdf",2,Color.rgb(140,175,195));b.putBoolean("ok",true);return b;}if(method.equals("break")){try(OutputStream out=new FileOutputStream(file("A/第3话.pdf"))){out.write("bad".getBytes());}b.putBoolean("ok",true);return b;}}catch(Exception e){throw new RuntimeException(e);}return super.call(method,arg,extras);}
}
