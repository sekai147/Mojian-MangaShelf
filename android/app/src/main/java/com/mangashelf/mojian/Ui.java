package com.mangashelf.mojian;

import android.content.Context;
import android.graphics.*;
import android.graphics.drawable.*;
import android.content.res.ColorStateList;
import android.view.*;
import android.widget.*;

final class Ui {
    static final int BG=Color.rgb(247,247,242), INK=Color.rgb(36,51,44), MUTED=Color.rgb(119,130,120), GREEN=Color.rgb(49,86,73), SOFT=Color.rgb(232,237,227), LINE=Color.rgb(224,229,219), BROWN=Color.rgb(169,123,86);
    static int dp(Context c,float n){return Math.round(n*c.getResources().getDisplayMetrics().density);}
    static GradientDrawable shape(int color,float radius,Context c){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(c,radius));return d;}
    static void surface(View v,int color,float radius){v.setBackground(shape(color,radius,v.getContext()));v.setClipToOutline(true);}
    static void ripple(View v,int color,float radius){Context c=v.getContext();v.setBackground(new RippleDrawable(ColorStateList.valueOf(0x18315649),shape(color,radius,c),null));v.setClipToOutline(true);}
    static TextView text(Context c,String text,int sp,int color,boolean bold){TextView t=new TextView(c);t.setText(text);t.setTextSize(sp);t.setTextColor(color);if(bold)t.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);t.setGravity(Gravity.CENTER_VERTICAL);t.setIncludeFontPadding(false);return t;}
    static LinearLayout column(Context c){LinearLayout l=new LinearLayout(c);l.setOrientation(LinearLayout.VERTICAL);return l;}
    static LinearLayout row(Context c){LinearLayout l=new LinearLayout(c);l.setOrientation(LinearLayout.HORIZONTAL);l.setGravity(Gravity.CENTER_VERTICAL);return l;}
    static LinearLayout.LayoutParams lp(Context c,int w,int h){return new LinearLayout.LayoutParams(w<0?w:dp(c,w),h<0?h:dp(c,h));}
    static void pad(View v,int x,int y){v.setPadding(dp(v.getContext(),x),dp(v.getContext(),y),dp(v.getContext(),x),dp(v.getContext(),y));}
    static void gap(LinearLayout l,int height){l.addView(new View(l.getContext()),lp(l.getContext(),1,height));}
    static TextView button(Context c,String title,boolean primary,Runnable action){TextView b=text(c,title,14,primary?Color.WHITE:GREEN,true);b.setGravity(Gravity.CENTER);pad(b,18,12);ripple(b,primary?GREEN:SOFT,16);b.setMinHeight(dp(c,48));b.setOnClickListener(v->action.run());return b;}
    static View iconButton(Context c,String name,String description,Runnable action){Icon icon=new Icon(c,name,GREEN);icon.setTag("icon-"+name);icon.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_YES);icon.setContentDescription(description);ripple(icon,Color.TRANSPARENT,16);icon.setOnClickListener(v->action.run());icon.setMinimumWidth(dp(c,48));icon.setMinimumHeight(dp(c,48));return icon;}
    static class Icon extends View {
        String name;int color;Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
        Icon(Context c,String name,int color){super(c);this.name=name;this.color=color;setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);}
        @Override protected void onDraw(Canvas canvas){super.onDraw(canvas);canvas.save();float size=dp(getContext(),23);canvas.translate((getWidth()-size)/2,(getHeight()-size)/2);canvas.scale(size/24,size/24);p.setColor(color);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(1.7f);p.setStrokeCap(Paint.Cap.ROUND);p.setStrokeJoin(Paint.Join.ROUND);
            Path path=new Path();
            switch(name){
            case "back":case "left":path.moveTo(15,5);path.lineTo(8,12);path.lineTo(15,19);break;
            case "right":path.moveTo(9,5);path.lineTo(16,12);path.lineTo(9,19);break;
            case "plus":canvas.drawLine(12,5,12,19,p);canvas.drawLine(5,12,19,12,p);break;
            case "close":canvas.drawLine(6,6,18,18,p);canvas.drawLine(18,6,6,18,p);break;
            case "check":path.moveTo(5,12);path.lineTo(10,17);path.lineTo(19,7);break;
            case "down":path.moveTo(7,10);path.lineTo(12,15);path.lineTo(17,10);break;
            case "more":p.setStyle(Paint.Style.FILL);for(int y=5;y<=19;y+=7)canvas.drawCircle(12,y,1.5f,p);break;
            case "search":canvas.drawCircle(10.5f,10.5f,6,p);canvas.drawLine(15,15,20,20,p);break;
            case "folder":path.moveTo(3,7);path.lineTo(3,19);path.lineTo(21,19);path.lineTo(21,7);path.lineTo(11,7);path.lineTo(9,4);path.lineTo(3,4);path.close();break;
            case "refresh":canvas.drawArc(4,4,20,20,35,290,false,p);path.moveTo(20,4);path.lineTo(20,10);path.lineTo(14,10);break;
            case "chapters":for(int y=6;y<=18;y+=6){canvas.drawCircle(4,y,.6f,p);canvas.drawLine(9,y,21,y,p);}break;
            case "settings":canvas.drawCircle(12,12,4,p);for(int i=0;i<8;i++){double a=i*Math.PI/4;canvas.drawLine(12+(float)Math.cos(a)*8,12+(float)Math.sin(a)*8,12+(float)Math.cos(a)*10,12+(float)Math.sin(a)*10,p);}canvas.drawCircle(12,12,8,p);break;
            case "play":p.setStyle(Paint.Style.FILL);path.moveTo(8,5);path.lineTo(19,12);path.lineTo(8,19);path.close();break;
            case "book":default:path.moveTo(3,4);path.quadTo(8,3,12,6);path.quadTo(16,3,21,4);path.lineTo(21,20);path.quadTo(16,19,12,21);path.quadTo(8,19,3,20);path.close();canvas.drawLine(12,6,12,21,p);break;
            }
            canvas.drawPath(path,p);canvas.restore();
        }
    }
    private Ui(){}
}
