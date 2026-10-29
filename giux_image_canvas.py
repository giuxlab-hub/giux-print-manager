# SPDX-License-Identifier: GPL-3.0-or-later
"""Pixel-accurate image selection with eight handles, pan and cursor zoom."""
from PIL import Image
import gi
gi.require_version("Gtk","3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf

class ImageCanvas(Gtk.DrawingArea):
    HANDLES=("nw","n","ne","e","se","s","sw","w")
    def __init__(self, path):
        super().__init__()
        self.image_path=None
        self.pixbuf=None
        self.iw=self.ih=1
        self.zoom=0.55
        self.selection=None
        self.drag=None
        self.scroller=None
        self.on_zoom=None
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.SCROLL_MASK |
                        Gdk.EventMask.SMOOTH_SCROLL_MASK)
        for event,callback in (("draw",self.draw),
                               ("button-press-event",self.press),
                               ("motion-notify-event",self.motion),
                               ("button-release-event",self.release),
                               ("scroll-event",self.scroll)):
            self.connect(event,callback)
        self.load_image(path)

    def load_image(self,path,preserve=False):
        with Image.open(path) as im:
            width,height=im.size
        self.pixbuf=GdkPixbuf.Pixbuf.new_from_file(str(path))
        self.iw,self.ih=width,height
        self.image_path=str(path)
        if not preserve:self.selection=None
        elif self.box():
            x1,y1,x2,y2=self.box()
            self.selection=(min(x1,width),min(y1,height),
                            min(x2,width),min(y2,height))
        self.resize_canvas()

    def resize_canvas(self):
        self.set_size_request(max(1,round(self.iw*self.zoom)),
                              max(1,round(self.ih*self.zoom)))
        self.queue_draw()

    def set_zoom(self,value,center=None):
        value=max(0.10,min(5.0,float(value)))
        previous=self.zoom
        if abs(value-previous)<1e-7:return
        hadj=vadj=None
        if self.scroller:
            hadj=self.scroller.get_hadjustment()
            vadj=self.scroller.get_vadjustment()
            if center is None:
                center=(hadj.get_page_size()/2,vadj.get_page_size()/2)
            # Find image-coordinate point beneath the cursor at the old zoom.
            xp=(hadj.get_value()+center[0])/previous
            yp=(vadj.get_value()+center[1])/previous
        self.zoom=value
        self.resize_canvas()
        if hadj and vadj:
            def reposition():
                hadj.set_value(max(hadj.get_lower(),min(hadj.get_upper()-hadj.get_page_size(),xp*value-center[0])))
                vadj.set_value(max(vadj.get_lower(),min(vadj.get_upper()-vadj.get_page_size(),yp*value-center[1])))
                return False
            from gi.repository import GLib
            GLib.idle_add(reposition)
        if self.on_zoom:self.on_zoom(value)

    def scroll(self,widget,event):
        if event.direction==Gdk.ScrollDirection.UP:factor=1.15
        elif event.direction==Gdk.ScrollDirection.DOWN:factor=1/1.15
        elif event.direction==Gdk.ScrollDirection.SMOOTH:
            factor=1.15**(-event.delta_y)
        else:return False
        if self.scroller:
            h=self.scroller.get_hadjustment()
            v=self.scroller.get_vadjustment()
            center=(event.x-h.get_value(),event.y-v.get_value())
        else:center=None
        self.set_zoom(self.zoom*factor,center)
        return True

    def pixels(self,x,y):
        return (max(0,min(self.iw,int(round(x/self.zoom)))),
                max(0,min(self.ih,int(round(y/self.zoom)))))

    def box(self):
        if not self.selection:return None
        a,b,c,d=self.selection
        x1,x2=sorted((a,c));y1,y2=sorted((b,d))
        if x2-x1<3 or y2-y1<3:return None
        return (x1,y1,x2,y2)

    def clear(self):
        self.selection=None;self.queue_draw()

    def handles(self):
        box=self.box()
        if not box:return {}
        x1,y1,x2,y2=box
        xm=(x1+x2)/2;ym=(y1+y2)/2
        return dict(zip(self.HANDLES,((x1,y1),(xm,y1),(x2,y1),
                                       (x2,ym),(x2,y2),(xm,y2),
                                       (x1,y2),(x1,ym))))

    def hit(self,point):
        # Fixed on-screen hit targets, regardless of image zoom.
        threshold=9/max(self.zoom,0.01)
        x,y=point
        for name,(hx,hy) in self.handles().items():
            if abs(x-hx)<=threshold and abs(y-hy)<=threshold:
                return name
        box=self.box()
        if box and box[0]<=x<=box[2] and box[1]<=y<=box[3]:
            return "move"
        return "new"

    def press(self,widget,event):
        if event.button==2 and self.scroller:
            h=self.scroller.get_hadjustment()
            v=self.scroller.get_vadjustment()
            self.drag=("pan",(event.x,event.y),(h.get_value(),v.get_value()))
            return True
        if event.button!=1:return False
        point=self.pixels(event.x,event.y)
        mode=self.hit(point)
        if mode=="new":
            self.selection=(*point,*point)
        self.drag=(mode,point,self.box() if mode!="new" else None)
        self.queue_draw()
        return True

    def motion(self,widget,event):
        if not self.drag:return False
        mode,start,original=self.drag
        if mode=="pan":
            h=self.scroller.get_hadjustment()
            v=self.scroller.get_vadjustment()
            h.set_value(max(0,original[0]-(event.x-start[0])))
            v.set_value(max(0,original[1]-(event.y-start[1])))
            return True
        point=self.pixels(event.x,event.y)
        if mode=="new":
            self.selection=(*start,*point)
        elif original:
            x1,y1,x2,y2=original
            if mode=="move":
                dx=point[0]-start[0];dy=point[1]-start[1]
                dx=max(-x1,min(self.iw-x2,dx))
                dy=max(-y1,min(self.ih-y2,dy))
                self.selection=(x1+dx,y1+dy,x2+dx,y2+dy)
            else:
                # Clamp and preserve at least 3 pixels; allow dragging past the opposite edge.
                x,y=point
                if "w" in mode:x1=min(x,x2-3)
                if "e" in mode:x2=max(x,x1+3)
                if "n" in mode:y1=min(y,y2-3)
                if "s" in mode:y2=max(y,y1+3)
                self.selection=(x1,y1,x2,y2)
        self.queue_draw()
        return True

    def release(self,widget,event):
        if self.drag and ((event.button==2 and self.drag[0]=="pan") or event.button==1):
            self.motion(widget,event)
            self.drag=None
            if self.box() is None:self.selection=None
            self.queue_draw()
            return True
        return False

    def draw(self,widget,ctx):
        ctx.set_source_rgb(.19,.20,.22)
        ctx.paint()
        ctx.save()
        ctx.scale(self.zoom,self.zoom)
        Gdk.cairo_set_source_pixbuf(ctx,self.pixbuf,0,0)
        ctx.paint()
        ctx.restore()
        box=self.box()
        if box:
            x1,y1,x2,y2=box
            ctx.rectangle(x1*self.zoom,y1*self.zoom,
                          (x2-x1)*self.zoom,(y2-y1)*self.zoom)
            ctx.set_source_rgba(.10,.43,.95,.16);ctx.fill_preserve()
            ctx.set_source_rgba(.05,.34,.94,1);ctx.set_line_width(2);ctx.stroke()
            for x,y in self.handles().values():
                left=x*self.zoom-4;top=y*self.zoom-4
                ctx.rectangle(left,top,8,8)
                ctx.set_source_rgb(1,1,1);ctx.fill_preserve()
                ctx.set_source_rgb(.03,.29,.89);ctx.set_line_width(1.5);ctx.stroke()
        return False
