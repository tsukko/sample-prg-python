import tkinter as tk
from tkinter import ttk
from sample_pdfminer2 import redraw_block
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class MyFrame(tk.Frame):
    """ Frame with three label """

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master.title('viewer.')

        # グラフの設定
        fig, ax1 = plt.subplots()
        fig.gca().set_aspect('equal', adjustable='box')  # グラフ領域の調整
        # キャンバスの生成
        self.Canvas = FigureCanvasTkAgg(fig, master=self)
        self.Canvas.get_tk_widget().grid(row=0, column=0, rowspan=10)

        # 各textboxの初期値と要素の定義
        row_index = 0
        # def_dev = "1"
        def_val_page = "13"
        def_val_exclude_header = "2"
        def_val_exclude_footer = "2"
        def_val_line_margin = "0.5"
        def_val_line_margin2 = "5.0"
        def_val_line_overlap = "0.5"
        def_val_char_margin = "2.0"
        def_val_word_margin = "0.1"
        def_val_boxes_flow = "0.1"

        # self.text_div = tk.Entry(self)
        self.text_page = tk.Entry(self)
        self.text_exclude_header = tk.Entry(self)
        self.text_exclude_footer = tk.Entry(self)
        self.text_line_margin = tk.Entry(self)
        # self.text_line_margin2 = tk.Entry(self)
        self.text_line_overlap = tk.Entry(self)
        self.text_char_margin = tk.Entry(self)
        self.text_word_margin = tk.Entry(self)
        self.text_boxes_flow = tk.Entry(self)

        # self.create_obj('分割数:', row_index, self.text_div, def_dev, False, 0)
        # row_index += 1

        # page num
        self.create_obj('page number:', row_index, self.text_page, def_val_page, False, 0)
        row_index += 1

        # ヘッダ、フッタとして扱う行数
        self.create_obj('ヘッダ除外行:', row_index, self.text_exclude_header, def_val_exclude_header, False, 0)
        row_index += 1
        self.create_obj('フッタ除外行:', row_index, self.text_exclude_footer, def_val_exclude_footer, False, 0)
        row_index += 1

        # line_margin
        self.create_obj('line_margin:', row_index, self.text_line_margin, def_val_line_margin, True, 100)
        row_index += 1

        # self.create_obj('line_margin2:', row_index, self.text_line_margin2, def_val_line_margin2, True, 1500)
        # row_index += 1

        # line_overlap
        self.create_obj('line_overlap:', row_index, self.text_line_overlap, def_val_line_overlap, True, 100)
        row_index += 1

        # char_margin
        self.create_obj('char_margin:', row_index, self.text_char_margin, def_val_char_margin, True, 3000)
        row_index += 1

        # word_margin
        self.create_obj('word_margin:', row_index, self.text_word_margin, def_val_word_margin, True, 3000)
        row_index += 1

        # boxes_flow
        self.create_obj('boxes_flow:', row_index, self.text_boxes_flow, def_val_boxes_flow, True, 100)
        row_index += 1

        # button
        change_button = tk.Button(self, text='Change', command=self.change_button)
        change_button.grid(row=row_index, column=1, padx=5, pady=5)
        quit_button = tk.Button(self, text='Quit', command=self.quit_button)
        quit_button.grid(row=row_index, column=2, padx=5, pady=5)

        self.DrawCanvas(self.Canvas, ax1)

    def create_obj(self, label_data, row_index, text_box, text_box_data, exists_bar, max_val):
        #
        label_page = tk.Label(self, text=label_data)
        label_page.grid(row=row_index, column=1, padx=5, pady=5)
        text_box.insert(tk.END, text_box_data)
        text_box.grid(row=row_index, column=2, padx=5, pady=5)

        if exists_bar:
            my_val = tk.DoubleVar(value=float(text_box_data) * 100)
            my_val.trace("w", lambda _a, _b, _c: self.change_value(text_box, my_val.get()))
            sc1 = ttk.Scale(self, variable=my_val, orient=tk.HORIZONTAL, length=200, from_=0, to=max_val)
            sc1.grid(row=row_index, column=3, padx=5, pady=5)

    def quit_button(self):
        self.quit()
        self.destroy()

    def change_button(self):
        # print("on_click")
        # # テキストボックスの内容を得る
        # s = self.text1.get()
        # # ダイアログを表示
        # mbox.showinfo('挨拶', s + 'さん、こんにちは!')
        ax = redraw_block(
            int(self.text_page.get()) - 1,
            int(self.text_exclude_header.get()),
            int(self.text_exclude_footer.get()),
            float(self.text_line_margin.get()),
            float(self.text_line_overlap.get()),
            float(self.text_char_margin.get()),
            float(self.text_word_margin.get()),
            float(self.text_boxes_flow.get()))

        self.DrawCanvas(self.Canvas, ax)

    def change_value(self, text, val):
        # print('value = %d' % val, text)
        text.delete(0, tk.END)
        text.insert(tk.END, val / 100)

        ax = redraw_block(
            1,
            float(self.text_line_margin.get()),
            0.0,
            float(self.text_line_overlap.get()),
            float(self.text_char_margin.get()),
            float(self.text_word_margin.get()),
            float(self.text_boxes_flow.get()),
            float(self.text_page.get()) - 1)

        self.DrawCanvas(self.Canvas, ax)

    def DrawCanvas(self, canvas, ax, colors="gray"):
        # value = EditBox.get()
        # if value != '':
        #     EditBox.delete(0, tkinter.END)
        #     ax.cla()  # 前の描画データの消去
        #     gridSize = int(value)
        #     gridSize = (gridSize * 2 + 1)  # 半区画の区切りを算出
        #
        #     # 区画の線を引く
        #     for i in np.array(range(gridSize)) * 90.0:
        #         ax.plot(np.array([i, i]), np.array([0.0, (gridSize - 1) * 90]), color=colors, linestyle="dashed")
        #         ax.plot(np.array([0.0, (gridSize - 1) * 90]), np.array([i, i]), color=colors, linestyle="dashed")
        #
        #         # 斜めの線を引く
        #         if (i / 90.0) % 2 == 1:
        #             ax.plot(np.array([0.0, i]), np.array([(gridSize - 1) * 90 - i, (gridSize - 1) * 90]), color=colors,
        #                     linestyle="dashed")
        #             ax.plot(np.array([(gridSize - 1) * 90 - i, (gridSize - 1) * 90]), np.array([0.0, i]), color=colors,
        #                     linestyle="dashed")
        #
        #             ax.plot(np.array([(gridSize - 1) * 90, i]), np.array([i, (gridSize - 1) * 90]), color=colors,
        #                     linestyle="dashed")
        #             ax.plot(np.array([i, 0.0]), np.array([0.0, i]), color=colors, linestyle="dashed")

        canvas.draw()  # キャンバスの描画
