import logging
import os
import datetime
import webapp2
import random
import string
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4, landscape, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.pdfgen import canvas


class MainHandler(webapp2.RequestHandler):
    def get(self):
        path = "index.html"
        self.response.out.write(template.render(path, {}))
    def post(self):
        self.response.headers['Content-Type'] = 'application/pdf'
        if self.request.get('q') == 'Download':
            self.response.headers['Content-Disposition'] = 'attachment; filename=latest.pdf' # Makes it a download
        doc = SimpleDocTemplate(self.response.out, pagesize=landscape(A4))
        elements = []
        _Slots = "abcdefgh"
        _SLOTS = "ABCDEFGH"
        # Fetch all the data from the submitted html form
        heads = list(self.request.get("head_"+h) for h in ("day_time","8","9","10","11","12","2","4"))
        theo_slots = list(slot.upper() for slot in _Slots if self.request.get("theo_"+slot))
        not_opted = list(slot.upper() for slot in _Slots if not slot.upper() in theo_slots)
        a_fri_lec = self.request.get("slot_a_4") not in ('','false','False')
        text_slots = dict((slot, self.request.get("text_"+slot.lower(), slot)) for slot in theo_slots)
        for each in text_slots:
            if not text_slots[each]:
                text_slots[each] = each
        prac_slots = list(slot for slot in _Slots if self.request.get("prac_"+slot))
        free_slot_mark = self.request.get("free_slot_mark", '')
        prac_batch = int(self.request.get("batch"))
        seminar = self.request.get("seminar")
        seminar_text = self.request.get("text_seminar")
        if not seminar_text:
            seminar_text = "Seminar"
        # Being safe
        if not 1 <= prac_batch <= 4:
            prac_batch = 1
        user_no_courses = len(theo_slots)
        data = [heads,
                ['Mon', 'C', 'A', 'B', 'H', 'G', free_slot_mark, free_slot_mark],
                ['Tue', 'A', 'C', 'D', 'E', 'F', free_slot_mark, free_slot_mark],
                ['Wed', 'D', 'E', 'F', 'A', 'B', free_slot_mark, free_slot_mark],
                ['Thu', 'B', 'G', 'H', 'C', 'D', free_slot_mark, free_slot_mark],
                ['Fri', 'A', 'F', 'E', 'G', 'H', free_slot_mark, free_slot_mark]]
        # Replace given text for checked slots
        if user_no_courses:
            for user_slot in theo_slots:
                for data_pos in range(1,6):                
                    for ex in range(1,6):
                        if data[data_pos][ex] == user_slot:
                            data[data_pos][ex] = text_slots[user_slot]
            for user_slot in not_opted: # Replace free slots with given marker
                for data_pos in range(1,6):                
                    for ex in range(1,6):
                        if data[data_pos][ex] == user_slot:
                            data[data_pos][ex] = free_slot_mark
        # A slot Friday Lecture?      
        if 'A' in theo_slots:
            if not a_fri_lec:
                data[5][1] = free_slot_mark
        # Practical Mess
        if not prac_slots and not seminar:
            col_width = 1.55
            for i in range(len(data)):
                data[i] = data[i][:-2]
        else: # Currently don't have slot data
            col_width = 1.2
            prac_slot_batchwise = {1:{'b':(1,1),'c':(1,2),'d':(5,1),'e':(5,2),'f':(3,2),'g':(2,0),'h':(3,1)},
                                   2:{'b':(2,1),'c':(2,2),'d':(1,1),'e':(1,2),'f':(5,2),'g':(3,0),'h':(5,1)},
                                   3:{'b':(3,1),'c':(3,2),'d':(2,1),'e':(2,2),'f':(1,2),'g':(5,0),'h':(1,1)},
                                   4:{'b':(5,1),'c':(5,2),'d':(3,1),'e':(3,2),'f':(2,2),'g':(1,0),'h':(2,1)}}
            for user_slot in prac_slots:
                divas, samay = prac_slot_batchwise[prac_batch][user_slot]
                if user_slot == 'g':
                    data[divas][6] = text_slots[user_slot.upper()]
                    data[divas][7] = text_slots[user_slot.upper()]
                data[divas][samay+5] = text_slots[user_slot.upper()]
            if seminar:
                data[4][6] = seminar_text
                
        t=Table(data,len(data[0])*[col_width*inch], 6*[1*inch])
        color_blue_head = Color(79.0/256,129.0/256,189.0/256,1)
        color_blue_dark = Color(167.0/256,191.0/256,222.0/256,1)
        color_blue_light = Color(211.0/256,223.0/256,238.0/256,1)
        color_prac = Color(240.0/256,155.0/256,155.0/256,1)
        color_text = Color(0,0,0,0.6)
        Table_Style = TableStyle([('ALIGN', (0,0),(-1,-1), 'CENTER'),
                               ('VALIGN',(0,0),(-1,-1), 'MIDDLE'),
                               ('FONTSIZE',(0,0),(-1,-1), 16),
                               ('TEXTCOLOR',(0,0),(-1,-1), color_text),
                               ('TEXTCOLOR',(0,0),(0,-1), colors.white),
                               ('TEXTCOLOR',(0,0),(-1,0), colors.white),
                               ('BACKGROUND',(0,0),(0,-1), color_blue_head),
                               ('BACKGROUND',(1,0),(-1,0), color_blue_head),
                               ('BACKGROUND',(1,1),(-1,1), color_blue_dark),
                               ('BACKGROUND',(1,2),(-1,2), color_blue_light),
                               ('BACKGROUND',(1,3),(-1,3), color_blue_dark),
                               ('BACKGROUND',(1,4),(-1,4), color_blue_light),
                               ('BACKGROUND',(1,5),(-1,5), color_blue_dark),
                               ('INNERGRID', (0,0), (-1,-1), 0.25, colors.white),
                               ('BOX', (0,0), (-1,-1), 0.25, colors.white),])
        if prac_slots or seminar:
            Table_Style.add('BACKGROUND',(6,1),(6,-1), color_prac)
            Table_Style.add('BACKGROUND',(7,1),(7,-1), color_prac)
        t.setStyle(Table_Style)
        elements.append(t)
        doc.build(elements)

class AboutHandler(webapp2.RequestHandler):
    def get(self):
        path = "about.html"
        self.response.out.write(template.render(path, {}))

app = webapp2.WSGIApplication([('/?', MainHandler),('/about/?', AboutHandler)], debug=True)
