import tkinter as tk
from tkinter import ttk
from sample_pdfminer2 import redraw_block
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class MyFrame(tk.Frame):
    """
    左側にmatplotlib.pyplotで生成したグラフ
    右側にラベル、テキストボックス、スケールなどのパラメータを設定するエリア
    を配置する。
    変更したパラメータから新しいグラフを描画する
    """

    def __init__(self, master=None):
        # 各textboxの初期値と要素の定義
        row_index = 0
        def_val_temp = "1.0"

        # フレームの生成
        tk.Frame.__init__(self, master)
        self.master.title('title:Viewer.')

        # グラフの生成と配置
        fig, ax1 = plt.subplots()
        fig.gca().set_aspect('equal', adjustable='box')  # グラフ領域の調整
        # キャンバスの生成
        self.Canvas = FigureCanvasTkAgg(fig, master=self)
        self.Canvas.get_tk_widget().grid(row=0, column=0, rowspan=10)

        # text_param という パラメータを設定するテキストボックスを生成する
        self.text_param = tk.Entry(self)
        self.create_obj('label name:', row_index, self.text_param, def_val_temp, 1000)
        # row_indexは、テキストボックスやボタンを配置するrowに設定される
        # もしボタンの上に新たにテキストボックスなどを配置するときに、固定値で入れていると修正がめんどうだったため変数化した
        row_index += 1

        # 変更ボタンと終了ボタンを生成する
        change_button = tk.Button(self, text='Change', command=self.change_button)
        change_button.grid(row=row_index, column=1, padx=5, pady=5)
        quit_button = tk.Button(self, text='Quit', command=self.quit_button)
        quit_button.grid(row=row_index, column=2, padx=5, pady=5)

        # 描画処理
        self.DrawCanvas(self.Canvas, ax1)

    def create_obj(self, label_data, row_index, text_box, text_box_data, max_val):
        """
        ラベル、テキストボックス、スケールの生成と配置
        """
        # ラベルの生成と配置
        label = tk.Label(self, text=label_data)
        label.grid(row=row_index, column=1, padx=5, pady=5)
        # テキストボックスの生成と配置
        text_box.insert(tk.END, text_box_data)
        text_box.grid(row=row_index, column=2, padx=5, pady=5)

        # スケール (ttk.Scale)の生成と配置
        # trace()で、つまみが動くと、change_value()を呼んでテキストボックスと同期させている
        my_val = tk.DoubleVar(value=float(text_box_data) * 100)
        my_val.trace("w", lambda _a, _b, _c: self.change_value(text_box, my_val.get()))
        sc1 = ttk.Scale(self, variable=my_val, orient=tk.HORIZONTAL, length=200, from_=0, to=max_val)
        sc1.grid(row=row_index, column=3, padx=5, pady=5)

    def quit_button(self):
        """
        Quit the app.
        """
        self.quit()
        self.destroy()

    def change_button(self):
        """
        変更ボタンを押して、テキストボックスで変更した値を計算ロジック側に渡して、グラフを再描画する
        """
        # FIXME テキストボックスの変更した値をスケールに反映させる
        # 変更した値を計算ロジック側に渡す
        ax = redraw_block(float(self.text_param.get()))
        self.DrawCanvas(self.Canvas, ax)

    def change_value(self, text, val):
        """
        スケールをずらして変更した値を計算ロジック側に渡して、グラフを再描画する
        :param text:
        :param val:
        """
        # スケールの値をテキストボックスに反映させる
        text.delete(0, tk.END)
        text.insert(tk.END, val / 100)

        ax = redraw_block(float(self.text_param.get()))
        self.DrawCanvas(self.Canvas, ax)

    def DrawCanvas(self, canvas, ax, colors="gray"):
        canvas.draw()
