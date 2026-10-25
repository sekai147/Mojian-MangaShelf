package com.mangashelf.mojian;

import java.text.Normalizer;
import java.util.Comparator;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Same chapter naming conventions as the desktop library; no Android dependency. */
public final class ChapterOrder {
    private static final String NUM = "[0-9零〇一二两三四五六七八九十百千万]+(?:\\.[0-9]+)?";
    private static final Pattern[] PATTERNS = {
        Pattern.compile("第\\s*(" + NUM + ")\\s*[话話章回集]"),
        Pattern.compile("(?:chapter|chap|ch|episode|ep)\\s*[._#-]?\\s*(\\d+(?:\\.\\d+)?)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("第\\s*(" + NUM + ")\\s*卷"),
        Pattern.compile("vol(?:ume)?\\s*[._#-]?\\s*(\\d+(?:\\.\\d+)?)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("[\\[【]\\s*(\\d+(?:\\.\\d+)?)\\s*[\\]】]")
    };
    private static final Pattern SPECIAL = Pattern.compile("番外|特典|外传|外傳|extra|special|omake", Pattern.CASE_INSENSITIVE);
    private static final Pattern TOKENS = Pattern.compile("\\d+(?:\\.\\d+)?|\\D+");
    public static Double number(String name) {
        String n = Normalizer.normalize(name, Normalizer.Form.NFKC).replaceFirst("(?i)\\.pdf$", "");
        for (Pattern p : PATTERNS) {
            Matcher m = p.matcher(n);
            if (m.find()) return chinese(m.group(1));
        }
        n = n.replaceAll("\\[[^\\]]*\\]|【[^】]*】|\\([^)]*\\)", " ");
        Matcher m = Pattern.compile("^\\s*(\\d+(?:\\.\\d+)?)(?=\\D|$)").matcher(n);
        if (m.find()) return Double.valueOf(m.group(1));
        m = Pattern.compile("(?:^|[\\s_\\-])(\\d+(?:\\.\\d+)?)\\s*$").matcher(n);
        return m.find() ? Double.valueOf(m.group(1)) : null;
    }
    static Double chinese(String value) {
        try { return Double.valueOf(value); } catch (NumberFormatException ignored) { }
        String s = value.replace('两','二').replace('〇','零');
        String digits = "零一二三四五六七八九";
        int total=0, section=0, n=0;
        if (!s.matches(".*[十百千万].*")) {
            StringBuilder out = new StringBuilder();
            for (char c : s.toCharArray()) { int d=digits.indexOf(c); if(d<0)return null; out.append(d); }
            return out.length()==0 ? null : Double.valueOf(out.toString());
        }
        for (char c : s.toCharArray()) {
            int d=digits.indexOf(c);
            if(d>=0) n=d;
            else if(c=='万') { total+=(section+n)*10000; section=n=0; }
            else { int unit=c=='十'?10:c=='百'?100:c=='千'?1000:0; if(unit==0)return null; section+=(n==0?1:n)*unit; n=0; }
        }
        return (double)(total+section+n);
    }
    public static int compare(String a, String b) {
        boolean sa=SPECIAL.matcher(a).find(), sb=SPECIAL.matcher(b).find();
        if(sa!=sb)return sa?1:-1;
        Double na=number(a), nb=number(b);
        if((na==null)!=(nb==null))return na==null?1:-1;
        if(na!=null && Double.compare(na,nb)!=0)return Double.compare(na,nb);
        return natural(a,b);
    }
    public static int natural(String a, String b) {
        Matcher ma=TOKENS.matcher(Normalizer.normalize(a,Normalizer.Form.NFKC).toLowerCase(Locale.ROOT));
        Matcher mb=TOKENS.matcher(Normalizer.normalize(b,Normalizer.Form.NFKC).toLowerCase(Locale.ROOT));
        while(true) {
            boolean ha=ma.find(), hb=mb.find();
            if(!ha||!hb)return Boolean.compare(ha,hb);
            String x=ma.group(), y=mb.group(); int c;
            if(Character.isDigit(x.charAt(0))&&Character.isDigit(y.charAt(0)))c=Double.compare(Double.parseDouble(x),Double.parseDouble(y));
            else c=x.compareTo(y);
            if(c!=0)return c;
        }
    }
    public static int start(int page,int total,boolean dual) {
        int p=Math.max(0,Math.min(page,Math.max(0,total-1)));
        return dual?p-p%2:p;
    }
    private ChapterOrder() {}
}
