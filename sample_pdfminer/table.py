from pdfminer.layout import LTCurve


# 表
class LTTableRect(LTCurve):

    def __init__(self, text, bbox, stroke=False, fill=False, evenodd=False, stroking_color=None,
                 non_stroking_color=None):
        (x0, y0, x1, y1) = bbox
        self.text = text
        LTCurve.__init__(self, 0, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], stroke, fill, evenodd,
                         stroking_color, non_stroking_color)
        return

    def get_text(self):
        return self.text


# text文章のブロック
class LTTextBlock(LTCurve):

    def __init__(self, text, bbox, stroke=False, fill=False, evenodd=False, stroking_color=None,
                 non_stroking_color=None):
        (x0, y0, x1, y1) = bbox
        self.text = text
        LTCurve.__init__(self, 0, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], stroke, fill, evenodd,
                         stroking_color, non_stroking_color)
        return

    def get_text(self):
        return self.text


# block
class LTBlock(LTCurve):

    def __init__(self, text, bbox, stroke=False, fill=False, evenodd=False, stroking_color=None,
                 non_stroking_color=None):
        (x0, y0, x1, y1) = bbox
        self.text = text
        LTCurve.__init__(self, 0, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], stroke, fill, evenodd,
                         stroking_color, non_stroking_color)
        return

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text