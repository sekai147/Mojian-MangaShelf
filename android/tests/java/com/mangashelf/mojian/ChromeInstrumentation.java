package com.mangashelf.mojian;

import android.app.*;
import android.content.*;
import android.content.pm.ActivityInfo;
import android.os.*;
import android.view.*;
import java.io.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Real animation-frame checks on an installed APK, after the ordinary reader suite. */
public class ChromeInstrumentation extends ReaderInstrumentation {
    AtomicBoolean watchFrames(){
        AtomicBoolean intermediate=new AtomicBoolean(false);
        ReaderChromeMotion motion=activity.chromeMotion;
        if(motion.animator!=null)motion.animator.addUpdateListener(a->{
            float value=motion.progress;
            if(value>.05f&&value<.95f&&activity.headerSlot.getVisibility()==View.VISIBLE
                &&Math.abs(activity.readerHeader.getAlpha()-value)<.01
                &&activity.headerSlot.getLayoutParams().height>0
                &&activity.headerSlot.getLayoutParams().height<motion.topHeight
                &&activity.readerHeader.getTranslationY()<0)intermediate.set(true);
        });
        return intermediate;
    }
    void waitMotion()throws Exception{Thread.sleep(420);waitForIdleSync();}
    void tap(View view)throws Exception{
        int[] xy=new int[2];ui(()->view.getLocationOnScreen(xy));float x=xy[0]+view.getWidth()/2f,y=xy[1]+view.getHeight()/2f;
        long t=SystemClock.uptimeMillis();sendPointerSync(MotionEvent.obtain(t,t,0,x,y,0));
        sendPointerSync(MotionEvent.obtain(t,t+50,1,x,y,0));Thread.sleep(750);waitForIdleSync();
    }
    @Override public void onStart(){Bundle result=new Bundle();try{
        activity=(MainActivity)startActivitySync(new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        ui(()->activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT));Thread.sleep(650);
        check(!activity.library.books.isEmpty(),"Run ordinary reader suite first");Library.Book book=activity.library.books.get(0);
        ui(()->{activity.prefs.edit().putBoolean("motion",true).putString("layout","single").apply();activity.openReader(book,0,0);});waitRender();
        AtomicBoolean[] hiding={null},showing={null};
        ui(()->{activity.toggleTools();hiding[0]=watchFrames();});waitMotion();
        check(hiding[0].get(),"Hide has real intermediate alpha, slide and reserved-height frames");
        check(activity.headerSlot.getVisibility()==View.GONE&&activity.footerSlot.getVisibility()==View.GONE,"Slots collapse after hiding");
        ui(()->{activity.toggleTools();showing[0]=watchFrames();});waitMotion();
        check(showing[0].get(),"Show has real intermediate frames");
        check(activity.readerHeader.getAlpha()==1&&activity.readerFooter.getAlpha()==1&&activity.readerHeader.getTranslationY()==0,"Shown bars finish fully visible");ok("toolbars_slide_fade_and_smoothly_resize_reader");
        ui(()->activity.toggleTools());Thread.sleep(65);ui(()->activity.toggleTools());Thread.sleep(55);ui(()->activity.toggleTools());Thread.sleep(60);ui(()->activity.toggleTools());waitMotion();
        check(activity.chrome&&activity.chromeMotion.progress==1&&activity.headerSlot.getVisibility()==View.VISIBLE,"Rapid taps finish at latest target");
        check((activity.getWindow().getDecorView().getSystemUiVisibility()&View.SYSTEM_UI_FLAG_FULLSCREEN)==0,"Cancelled hide cannot restore fullscreen");ok("rapid_toolbar_toggles_reverse_without_stale_callbacks");
        ui(()->{activity.prefs.edit().putBoolean("motion",false).apply();activity.toggleTools();});
        check(activity.chromeMotion.animator==null&&activity.chromeMotion.progress==0&&activity.headerSlot.getVisibility()==View.GONE,"Motion preference disables transition");
        ui(()->activity.toggleTools());check(activity.chromeMotion.progress==1,"Disabled motion shows instantly");ok("toolbar_animation_respects_motion_preference");
        ui(()->{activity.prefs.edit().putBoolean("motion",true).apply();activity.toggleTools();});Thread.sleep(50);
        ui(()->activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE));Thread.sleep(700);waitMotion();
        check(!activity.chrome&&activity.headerSlot.getVisibility()==View.GONE,"Rotation during hide settles correctly");
        ui(()->activity.toggleTools());waitMotion();check(activity.chromeMotion.bottomHeight==Ui.dp(activity,52),"Landscape footer remeasured");ok("toolbar_animation_survives_rotation_and_reflow");
        ReaderChromeMotion old=activity.chromeMotion;ui(()->activity.toggleTools());Thread.sleep(40);ui(()->activity.closeReader());waitMotion();
        check(old.disposed&&old.animator==null&&activity.location.equals("library"),"Leaving reader cancels old animation");
        check((activity.getWindow().getDecorView().getSystemUiVisibility()&View.SYSTEM_UI_FLAG_FULLSCREEN)==0,"Library does not inherit delayed fullscreen");ok("leaving_reader_cancels_toolbar_motion");
        ui(()->{activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);activity.prefs.edit().putString("layout","webtoon").apply();activity.openReader(book,0,0);});Thread.sleep(600);
        long end=SystemClock.uptimeMillis()+20000;while(SystemClock.uptimeMillis()<end){waitForIdleSync();if(activity.webtoonView.announced&&activity.webtoonView.pending.isEmpty())break;Thread.sleep(50);}
        check(activity.webtoonView.announced,"Webtoon loaded");
        ui(()->activity.webtoonView.jumpTo(0,0,.37));Thread.sleep(450);waitForIdleSync();double offset=activity.webtoonView.offset;
        tap(activity.webtoonView);check(!activity.chrome&&activity.headerSlot.getVisibility()==View.GONE,"Real central tap hides webtoon bars");
        tap(activity.webtoonView);check(activity.chrome&&activity.footerSlot.getVisibility()==View.VISIBLE,"Real central tap shows webtoon bars");
        check(Math.abs(activity.webtoonView.offset-offset)<.001,"Animation preserves webtoon reading position");ok("real_webtoon_taps_animate_bars_without_losing_position");
        ui(()->activity.closeReader());ui(()->activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED));
        result.putString("stream",passed.size()+" toolbar checks passed\n"+String.join("\n",passed));finish(Activity.RESULT_OK,result);
    }catch(Throwable e){try{screenshot("toolbar-failure");}catch(Exception ignored){}StringWriter trace=new StringWriter();e.printStackTrace(new PrintWriter(trace));result.putString("stream","FAILED\n"+trace);finish(Activity.RESULT_CANCELED,result);}}
}
