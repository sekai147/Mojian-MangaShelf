package com.mangashelf.mojian;

import android.content.Context;
import android.graphics.*;
import android.view.*;
import android.animation.ValueAnimator;

/** Flat PDF spread: no synthetic paper, spine, border or shadow. */
final class PageView extends View {
    interface Actions {void turn(int physicalDirection);void toggleChrome();}
    Bitmap bitmap; final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
    final GestureDetector gestures;final ScaleGestureDetector scales;final Actions actions;
    float zoom=1,offsetX=0,offsetY=0,transition=1;boolean fitWidth=false,transforming=false;
    int effect=0,direction=1;ValueAnimator animator;
    PageView(Context context,Actions actions) {
        super(context);this.actions=actions;setContentDescription("漫画页面；左右滑动翻页，双指缩放，轻点中央隐藏工具栏");setFocusable(true);
        scales=new ScaleGestureDetector(context,new ScaleGestureDetector.SimpleOnScaleGestureListener(){
            @Override public boolean onScaleBegin(ScaleGestureDetector detector){transforming=true;return true;}
            @Override public boolean onScale(ScaleGestureDetector detector){zoom=Math.max(1,Math.min(5,zoom*detector.getScaleFactor()));clamp();invalidate();return true;}
        });
        gestures=new GestureDetector(context,new GestureDetector.SimpleOnGestureListener(){
            @Override public boolean onDown(android.view.MotionEvent e){return true;}
            @Override public boolean onDoubleTap(android.view.MotionEvent e){zoom=zoom>1.1f?1:2.5f;offsetX=offsetY=0;clamp();invalidate();return true;}
            @Override public boolean onSingleTapConfirmed(android.view.MotionEvent e){
                if(e.getX()<getWidth()*.23f)actions.turn(-1);else if(e.getX()>getWidth()*.77f)actions.turn(1);else actions.toggleChrome();performClick();return true;
            }
            @Override public boolean onScroll(android.view.MotionEvent a,android.view.MotionEvent b,float dx,float dy){
                if(scales.isInProgress())return true;
                if(zoom>1.01f||fitWidth){offsetX-=dx;offsetY-=dy;clamp();invalidate();}return true;
            }
            @Override public boolean onFling(android.view.MotionEvent a,android.view.MotionEvent b,float vx,float vy){
                if(!transforming&&zoom<=1.01f&&Math.abs(vx)>Math.abs(vy)*1.4&&Math.abs(b.getX()-a.getX())>getWidth()*.1f){actions.turn(vx<0?1:-1);return true;}return false;
            }
        });
    }
    @Override public boolean onTouchEvent(android.view.MotionEvent event){
        if(event.getActionMasked()==android.view.MotionEvent.ACTION_DOWN)transforming=false;
        if(event.getPointerCount()>1)transforming=true;
        scales.onTouchEvent(event);gestures.onTouchEvent(event);return true;
    }
    @Override public boolean performClick(){return super.performClick();}
    float baseScale(){if(bitmap==null||getWidth()==0)return 1;float width=(float)getWidth()/bitmap.getWidth();return fitWidth?width:Math.min(width,(float)getHeight()/bitmap.getHeight());}
    void clamp(){if(bitmap==null)return;float s=baseScale()*zoom;float mx=Math.max(0,(bitmap.getWidth()*s-getWidth())/2f),my=Math.max(0,(bitmap.getHeight()*s-getHeight())/2f);offsetX=Math.max(-mx,Math.min(mx,offsetX));offsetY=Math.max(-my,Math.min(my,offsetY));}
    void setBitmap(Bitmap value,int direction,int effect,boolean animate){
        if(animator!=null)animator.cancel();Bitmap old=bitmap;bitmap=value;zoom=1;offsetX=offsetY=0;this.direction=direction;this.effect=effect;transition=1;
        if(animate&&effect!=3){transition=0;animator=ValueAnimator.ofFloat(0,1);animator.setDuration(220);animator.addUpdateListener(a->{transition=(float)a.getAnimatedValue();invalidate();});animator.start();}
        invalidate();if(old!=null&&old!=value&&!old.isRecycled())old.recycle();
    }
    void dispose(){if(animator!=null)animator.cancel();if(bitmap!=null&&!bitmap.isRecycled())bitmap.recycle();bitmap=null;}
    @Override protected void onDraw(Canvas c){
        super.onDraw(c);if(bitmap==null||bitmap.isRecycled())return;
        float s=baseScale()*zoom;float w=bitmap.getWidth()*s,h=bitmap.getHeight()*s;
        c.save();c.translate((getWidth()-w)/2+offsetX,(getHeight()-h)/2+offsetY);
        if(transition<1){if(effect==0)c.translate((1-transition)*getWidth()*.14f*direction,0);else if(effect==2){c.translate(w*(1-transition)*.04f,h*(1-transition)*.04f);c.scale(.92f+.08f*transition,.92f+.08f*transition);}paint.setAlpha((int)(255*(.35f+.65f*transition)));}else paint.setAlpha(255);
        c.drawBitmap(bitmap,null,new RectF(0,0,w,h),paint);c.restore();
    }
}
