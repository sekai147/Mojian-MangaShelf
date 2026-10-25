package com.mangashelf.mojian;

import android.graphics.*;
import android.graphics.pdf.PdfRenderer;
import android.os.ParcelFileDescriptor;
import java.io.File;

final class PdfEngine {
    static final class Spread {
        Bitmap bitmap; int first, last, total;
        Spread(Bitmap b,int f,int l,int t){bitmap=b;first=f;last=l;total=t;}
    }
    static Spread render(File file,int requested,boolean dual,boolean rtl,int width,int height) throws Exception {
        try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(file,ParcelFileDescriptor.MODE_READ_ONLY);PdfRenderer renderer=new PdfRenderer(fd)) {
            int total=renderer.getPageCount();
            if(total==0)throw new java.io.IOException("PDF 没有可阅读页面");
            int first=ChapterOrder.start(requested,total,dual),last=Math.min(first+(dual?1:0),total-1);
            int count=last-first+1;int[] widths=new int[count],heights=new int[count];int maxH=0;
            for(int i=0;i<count;i++)try(PdfRenderer.Page p=renderer.openPage(first+i)){widths[i]=p.getWidth();heights[i]=p.getHeight();maxH=Math.max(maxH,heights[i]);}
            float logicalWidth=0;for(int i=0;i<count;i++)logicalWidth+=(float)widths[i]*maxH/heights[i];
            int gap=count==2?Math.max(4,width/180):0;
            // Render beyond screen resolution for pinch zoom, with a strict memory budget.
            float scale=Math.min((Math.max(320,width)*1.65f-gap)/logicalWidth,Math.max(600,height)*2f/maxH);
            scale=Math.min(scale,(float)Math.sqrt(5_000_000d/(logicalWidth*maxH)));
            int outH=Math.max(1,Math.round(maxH*scale));int[] outW=new int[count];int outWidth=gap;
            for(int i=0;i<count;i++){outW[i]=Math.max(1,Math.round((float)widths[i]*maxH/heights[i]*scale));outWidth+=outW[i];}
            Bitmap result=Bitmap.createBitmap(outWidth,outH,Bitmap.Config.ARGB_8888);
            try {
                Canvas canvas=new Canvas(result);int x=0;
                for(int order=0;order<count;order++) {
                    if(Thread.currentThread().isInterrupted())throw new java.io.InterruptedIOException();
                    int i=rtl?count-1-order:order;
                    try(PdfRenderer.Page page=renderer.openPage(first+i)) {
                        Bitmap part=Bitmap.createBitmap(outW[i],outH,Bitmap.Config.ARGB_8888);
                        try{part.eraseColor(Color.WHITE);page.render(part,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);canvas.drawBitmap(part,x,0,null);}finally{part.recycle();}
                    }
                    x+=outW[i]+gap;
                }
                return new Spread(result,first,last,total);
            } catch(Exception|OutOfMemoryError e){result.recycle();throw e;}
        }
    }
    private PdfEngine(){}
}
