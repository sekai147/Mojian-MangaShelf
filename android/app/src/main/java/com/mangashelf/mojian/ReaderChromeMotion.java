package com.mangashelf.mojian;

import android.animation.*;
import android.view.*;
import android.view.animation.PathInterpolator;
import android.widget.*;
import java.util.function.Consumer;

/** Reversible toolbar motion, including the space reserved by the reader layout. */
final class ReaderChromeMotion {
    final FrameLayout topSlot, bottomSlot;
    final View top, bottom;
    final Consumer<Boolean> systemBars;
    ValueAnimator animator;
    float progress=1;
    int topHeight, bottomHeight, generation=0;
    boolean visible=true, disposed=false;

    static FrameLayout wrap(LinearLayout parent,View bar) {
        FrameLayout slot=new FrameLayout(parent.getContext());
        slot.setClipChildren(true);slot.setClipToPadding(true);
        slot.addView(bar,new FrameLayout.LayoutParams(-1,-2));
        parent.addView(slot,new LinearLayout.LayoutParams(-1,-2));
        return slot;
    }

    ReaderChromeMotion(FrameLayout topSlot,View top,FrameLayout bottomSlot,View bottom,
                       Consumer<Boolean> systemBars) {
        this.topSlot=topSlot;this.top=top;this.bottomSlot=bottomSlot;this.bottom=bottom;
        this.systemBars=systemBars;reflow();
    }

    int measure(View bar,FrameLayout slot) {
        int width=slot.getWidth();
        if(width<=0&&slot.getParent() instanceof View)width=((View)slot.getParent()).getWidth();
        if(width<=0)width=bar.getResources().getDisplayMetrics().widthPixels;
        bar.measure(View.MeasureSpec.makeMeasureSpec(width,View.MeasureSpec.EXACTLY),
                    View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED));
        return Math.max(1,bar.getMeasuredHeight());
    }

    void reflow() {
        if(disposed)return;
        topHeight=measure(top,topSlot);bottomHeight=measure(bottom,bottomSlot);
        FrameLayout.LayoutParams t=(FrameLayout.LayoutParams)top.getLayoutParams();
        t.height=topHeight;top.setLayoutParams(t);
        FrameLayout.LayoutParams b=(FrameLayout.LayoutParams)bottom.getLayoutParams();
        b.height=bottomHeight;bottom.setLayoutParams(b);
        apply();
    }

    void apply() {
        top.setAlpha(progress);bottom.setAlpha(progress);
        top.setTranslationY(-topHeight*(1-progress));
        // Collapsing the bottom slot already moves it toward the bottom screen edge.
        bottom.setTranslationY(bottomHeight*.15f*(1-progress));
        resize(topSlot,Math.round(topHeight*progress));
        resize(bottomSlot,Math.round(bottomHeight*progress));
    }

    void resize(FrameLayout slot,int height) {
        LinearLayout.LayoutParams p=(LinearLayout.LayoutParams)slot.getLayoutParams();
        if(p.height!=height){p.height=height;slot.setLayoutParams(p);}
    }

    void setVisible(boolean show,boolean animate) {
        if(disposed)return;
        visible=show;int token=++generation;
        if(animator!=null){animator.cancel();animator=null;}
        topSlot.setVisibility(View.VISIBLE);bottomSlot.setVisibility(View.VISIBLE);
        topSlot.setImportantForAccessibility(show?View.IMPORTANT_FOR_ACCESSIBILITY_AUTO:View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS);
        bottomSlot.setImportantForAccessibility(show?View.IMPORTANT_FOR_ACCESSIBILITY_AUTO:View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS);
        if(show)systemBars.accept(true);
        float target=show?1:0;
        if(!animate||Math.abs(progress-target)<.0001f){progress=target;apply();finish(token);return;}
        ValueAnimator motion=ValueAnimator.ofFloat(progress,target);animator=motion;
        motion.setDuration(Math.max(90,Math.round(250*Math.abs(progress-target))));
        motion.setInterpolator(new PathInterpolator(.2f,0,.2f,1));
        motion.addUpdateListener(a->{if(!disposed&&generation==token){progress=(float)a.getAnimatedValue();apply();}});
        motion.addListener(new AnimatorListenerAdapter(){
            @Override public void onAnimationEnd(Animator animation){finish(token);}
        });
        motion.start();
    }

    void finish(int token) {
        if(disposed||generation!=token)return;
        animator=null;progress=visible?1:0;apply();
        topSlot.setVisibility(visible?View.VISIBLE:View.GONE);
        bottomSlot.setVisibility(visible?View.VISIBLE:View.GONE);
        systemBars.accept(visible);
    }

    void dispose() {
        disposed=true;generation++;
        if(animator!=null){animator.cancel();animator=null;}
    }
}
