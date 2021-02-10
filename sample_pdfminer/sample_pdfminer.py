import os
import cv2
import csv
import glob
import shutil
from pdfminer.converter import PDFPageAggregator, PDFConverter
from pdfminer.layout import LAParams, LTContainer, LTTextBox, LTChar, LTFigure, LTImage, LTLine, LTRect, LTCurve, LTPage
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.image import ImageWriter

from table import LTTableRect, LTBlock, LTTextBlock

import matplotlib.pyplot as plt

'''''
FIXME デバッグしやすいようにコーディング規約PEP8を無視したり、
無駄な書き方をしたままのところが残っている

pdfminer.six について
https://euske.github.io/pdfminer/programming.html

- LTPage
　child objects
　->　LTTextBox, LTFigure, LTImage, LTRect, LTCurve and LTLine
- LTTextBox -> a list of LTTextLine objects. -> a list of LTChar objects.
- LTFigure  -> figures or pictures. 子にLTImageやLTCurveを持つ
- LTImage   -> Embedded images can be in JPEG or other formats
- LTLine    -> a single straight line. 表　LTCurveを継承
- LTRect    -> a rectangle. 長方形　LTCurveを継承
- LTCurve   -> Bezier curve. 曲線

添付文書は、ネットで薬で検索した適当なPDFで確認

コマンド例
python venv\Scripts\pdf2txt.py input\a.pdf -t xml -o a.xml -O outputDir
python venv\Scripts\pdf2txt.py input\a.pdf -t txt -o a.txt -O outputDir


TODO
PDFの仕様理解
ページや列をまたいだブロックの結合
インデントによるブロック分け
フォントによるmargin変更
さまざまなmarginによる結果一覧を自動計算
'''''

'''パラメータ　ここから'''
# 分割数
division_number = 2
input_pdf_dir = "input"
output_dir = "output_pmn"
output_image_dir = output_dir + "/img"
intermediate_dir = "Intermediate_img"
# 見た目は線は表の内側にあるのに、座標は外側を示しているケースがあり、
# 誤差とみなして判断するための値
acceptable_range: float = 5.0
# 右列のLTTextBoxのx座標が結構ぶれる（左列の座標に入ったり）ので、許容範囲を設定する
acceptable_range_x: float = 4.0
# LTRectで、グラフなどを示す。小さな図形などを拾いまくるので、最小サイズを設定する
graph_min_size: float = 20.0
title_center_range: float = 100.0
line_overlap = 0.5  # 0.5
line_margin = 0.4  # 0.5  # 添付文書は、0.4
line_margin2 = 5.0  # 添付文書は、5.0 # しおりは、3.13。3.192以下であること
'''パラメータ　ここまで'''

# debug_flag_save_table = False
debug_flag_save_table = True


# 結果の出力用ディレクトリが存在していれば、クリアして再生成する
def output_setting():
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(output_dir)
    os.makedirs(output_image_dir)


# PDF解析用の初期設定
def analyze_setting() -> (PDFPageInterpreter, PDFPageAggregator):
    # Layout Analysisのパラメーターを設定。縦書きの検出を有効にする。
    laparams = LAParams(line_overlap=line_overlap,
                        char_margin=15.0,  # 2.0,
                        line_margin=line_margin,  # 0.5,
                        word_margin=15.0,  # 0.1,
                        boxes_flow=0.1,  # 0.5,
                        detect_vertical=True,
                        all_texts=True)
    # char_margin (M)
    # line_margin (L)
    # word_margin (W),
    # LAParams boxes flow (F)

    # 共有のリソースを管理するリソースマネージャーを作成。
    resource_manager = PDFResourceManager()

    # ページを集めるPageAggregatorオブジェクトを作成。
    dev = PDFPageAggregator(resource_manager, laparams=laparams)

    # imagewriter = ImageWriter('outputImg')
    # dev = PDFConverter(resource_manager, 'outputImg', laparams=laparams)

    # PDFPageInterpreterオブジェクトを作成。
    itp = PDFPageInterpreter(resource_manager, dev)

    return itp, dev


# フッターかどうかを判断する。
def is_footer(obj, division_width, height):
    '''
_objs = {list} <class 'list'>: [<LTTextLineHorizontal 330.728,96.897,355.208,109.899 '̶２̶\n'>]
bbox = {tuple} <class 'tuple'>: (330.727816, 96.897016, 355.207916, 109.89901599999999)
height = {float} 13.001999999999995
index = {int} 46
width = {float} 24.480099999999993
x0 = {float} 330.727816
x1 = {float} 355.207916
y0 = {float} 96.897016
y1 = {float} 109.89901599999999

division_width = {float} 354.331
height = {float} 955.276
width = {float} 708.662

height / 15 =
63.68506666666667
    '''
    # TODO 値の正当性を検討
    conditions1 = obj.x0 - 10 < division_width < obj.x1 + 10
    conditions2 = obj.x1 - obj.x0 < 30
    conditions3 = obj.y0 < height / 8
    return conditions1 and conditions2 and conditions3


# 再帰的なオブジェクトから子オブジェクトを抽出してリスト化する
def find_object_recursively(layout_obj):
    # LTTextBoxを継承するオブジェクトの場合は1要素のリストを返す。
    # print("obj_name:", layout_obj.__class__.__name__)
    if isinstance(layout_obj, LTTextBox):
        return [layout_obj]

    if isinstance(layout_obj, LTImage):
        # print("LTImage:", layout_obj.__class__.__name__)
        imagewriter = ImageWriter(output_image_dir)
        imagewriter.export_image(layout_obj)
        # TODO jpeg以外の画像を抽出したい（PDFMinerでは不可ぽい）
        # stream = child_fig.stream
        # filters = stream.get_filters()
        # (width, height) = child_fig.srcsize
        # print("width, height, len(filters), filters[0][0]:", width, height, len(filters), filters[0][0])
        # ext = '_.%d.%dx%d.img' % (child_fig.bits, width, height)
        # name = child_fig.name + ext
        # print(child_fig.bits, name, child_fig.colorspace)
        # if filters[0][0] in LITERALS_FLATE_DECODE:
        #     with open('outputImg/' + name, "wb") as fp:
        #         # imgdata = zlib.decompress(stream.data)
        #         data = stream.get_data()
        #         fp.write(data)
        #         fp.close()
        return [layout_obj]

    if isinstance(layout_obj, LTLine):
        return [layout_obj]
    if isinstance(layout_obj, LTRect):
        return [layout_obj]
    # LTLine も LTRect も、LTCurve を継承しているので、これで両方とも返る
    # if isinstance(layout_obj, LTCurve):
    #     return [layout_obj]

    # LTPageやLTFigureなど、LTContainerを継承するオブジェクトは子要素を含むので、再帰的に探す。
    # if isinstance(layout_obj, LTPage):
    if isinstance(layout_obj, LTContainer):
        boxes = []
        for child_con in layout_obj:
            boxes.extend(find_object_recursively(child_con))

        return boxes

    # print("none object:", layout_obj.__class__.__name__)
    return []  # その他の場合は空リストを返す。


# オブジェクトを並び替えてたりして、ブロックをつくる
def create_block(object_list, height, width):
    # 多重リストのまま返却してもらう
    sort_lists = sort_object(object_list, height, width)
    # 表の抽出とTextグループの計算（一つのメソッドでまとめられるが、わかりやすさのために現状は分けている）
    table_lists = create_table_object(sort_lists)
    text_group_lists = create_text_group_object(sort_lists)
    # 表とTextグループをブロックとしてまとめる
    block_lists = create_block_object(table_lists, text_group_lists)

    # LTBlockクラスにテキストを入れる
    # FIXME 表、かつ、Textグループに属するTextがあるため、ここで、再度ループ処理を行ってしまっている
    block_text_lists = insert_text_in_block(sort_lists, block_lists)

    # # 一つのListにまとめる
    res_list = []
    for index, tmp_list in enumerate(sort_lists):
        tmp_list.extend(block_text_lists[index])
        tmp_list.sort(key=lambda b: -b.y1)
        for data in tmp_list:
            res_list.append(data)

    aaa = []
    for tmp_list in block_text_lists:
        for data in tmp_list:
            aaa.append(data)
    # res_list.extend(block_list)
    return res_list, aaa


# オブジェクトを並び替える
def sort_object(object_list, height, width):
    # PDFが中段で分かれている場合（xの中間より左側、右側で分ける）
    # 分割したときの列を判断する幅
    division_width = width / division_number
    temp_lists = [[] for i in range(division_number * 4)]
    body_region: int = 0

    # 最初にy方向でsort
    # テキストボックスの左上の座標の順でテキストボックスをソートする。
    # y1（Y座標の値）は上に行くほど大きくなるので、正負を反転させている。
    object_list.sort(key=lambda b: -b.y1)

    for obj in object_list:
        # LTLineだと拾えないケースがあった
        if isinstance(obj, LTCurve):
            # if isinstance(obj, LTLine) or isinstance(obj, LTRect):
            # Lineの幅が、半分以上だと、表ではなく、区切り線とみなす
            if obj.x1 - obj.x0 > division_width:
                if body_region < division_number * (4 - 1):
                    body_region += division_number
                continue
            if obj.x0 < 0:
                # マイナス座標のxが存在する
                continue
        if is_footer(obj, division_width, height):
            continue

        # かなり無理やり。
        # 右と左の列を分けるほかに、長い横線があると別領域と判断して、多重リストとして分ける
        if isinstance(obj, LTTextBox):
            test1 = obj.x0 + acceptable_range_x
            test2 = int((obj.x0 + acceptable_range_x) // division_width) + body_region
            temp_lists[int((obj.x0 + acceptable_range_x) // division_width) + body_region].append(obj)
        else:
            temp_lists[int(obj.x0 // division_width) + body_region].append(obj)

    # # 一つのListにまとめる
    # res_list = []
    # for tmp_list in temp_lists:
    #     for data in tmp_list:
    #         res_list.append(data)

    return temp_lists


# 表オブジェクトを作る、
def create_table_object(sort_lists):
    # 注意！　y座標は、y1が上
    # table_lists = [[] for i in range(len(sort_lists))]
    table_lists = []
    for index, s_list in enumerate(sort_lists):
        # print("s_list",index,  s_list)
        table_list = []
        line_num: int = 0
        o_x0: float = 0.0
        o_y0: float = 0.0
        o_x1: float = 0.0
        o_y1: float = 0.0
        o_text = ""
        # tmp_line_width = 0
        for box in s_list:
            # FIXME 8.pdfとかは、LTRectで表が作られている。LTLineはない
            # isv01lpd.pdfは、LTRectでとると0.pngでおかしなBlockができてしまう
            if isinstance(box, (LTRect, LTLine)):
                # print("0:\t", o_x0, o_y0, o_x1, o_y1, line_num, box)
                if o_x0 == 0.0 and o_y0 == 0.0:
                    # 1. 最初のLine位置を定義
                    o_x0, o_y0, o_x1, o_y1, line_num = box.x0, box.y0, box.x1, box.y1, line_num + 1
                    # tmp_line_width = box.linewidth
                    # print("1-1:\t", o_x0, o_y0, o_x1, o_y1, line_num)
                else:
                    # y座標がほぼ同じなら同じ表とみなし、x終点を変更
                    # Lineの始点が同じ場合、表の下部の線と想定
                    if ((abs(box.y0 - o_y0) < acceptable_range or abs(box.y1 - o_y1) < acceptable_range)
                        and o_x0 - acceptable_range < box.x0 < o_x1 + acceptable_range) \
                            or (o_y0 < box.y0 < o_y1 and o_y0 < box.y1 < o_y1):
                        o_x0 = min(box.x0, o_x0)
                        o_y0 = min(box.y0, o_y0)
                        o_x1 = max(box.x1, o_x1)
                        o_y1 = max(box.y1, o_y1)
                        line_num += 1
                        # print("2-1:\t", o_x0, o_y0, o_x1, o_y1, line_num, box)
                    elif (abs(o_x0 - box.x0) < acceptable_range or abs(o_x1 - box.x1) < acceptable_range
                          or (o_x0 < box.x0 < o_x1 and o_x0 < box.x1 < o_x1)) \
                            and abs(box.y1 - o_y0) < acceptable_range:
                        # 上のy0、y1で一致しなかった場合、
                        o_x0 = min(box.x0, o_x0)
                        o_y0 = min(box.y0, o_y0)
                        o_x1 = max(box.x1, o_x1)
                        o_y1 = max(box.y1, o_y1)
                        line_num += 1
                        # print("2-2:\t", o_x0, o_y0, o_x1, o_y1, line_num, box)
                    else:
                        # 表の終わり？
                        if line_num >= 4 and (abs(o_x1 - o_x0) > graph_min_size and abs(o_y0 - o_y1) > graph_min_size):
                            # print("box1:\t", (o_x0, o_y0, o_x1, o_y1), line_num)
                            table_list.append(LTTableRect(o_text, (o_x0, o_y0, o_x1, o_y1)))
                        if box.y1 - box.y0 > 800:
                            # FIXME 15.pdfのように左端に大きな縦線がある場合に無視する。値は苦し紛れ
                            o_x0, o_y0, o_x1, o_y1, line_num = 0.0, 0.0, 0.0, 0.0, 0
                        else:
                            o_x0, o_y0, o_x1, o_y1, o_text, line_num = box.x0, box.y0, box.x1, box.y1, "", 1
                        # print("1-2:\t", o_x0, o_y0, o_x1, o_y1, line_num)
            elif isinstance(box, LTTextBox):
                # 直前に、Lineがなかった場合(tmpX0 == 0.0)は、表でないので次に行く
                if o_x0 == 0.0:
                    continue
                # Lineがあった状態で、TextBoxが来た場合、Textのx座標がLine内にあると、次に行く
                elif o_x0 - acceptable_range < box.x0 < o_x1 + acceptable_range \
                        and o_x0 - acceptable_range < box.x1 < o_x1 + acceptable_range:
                    # print("4:\t", box.get_text(), o_x0, o_y0, o_x1, o_y1, line_num)
                    # o_text += box.get_text()
                    continue
            elif isinstance(box, LTRect) or isinstance(box, LTCurve):
                # グラフもざっくりと判定する（小さいLTRectが結構できるので、ある程度の大きさがないとグラフ扱いしない）
                if box.x0 > 0 and abs(box.x1 - box.x0) > graph_min_size and abs(box.y1 - box.y0) > graph_min_size:
                    # print("LTRect:\t", (box.x0, box.y0, box.x1, box.y1), line_num)
                    table_list.append(LTTableRect("LTRect", (box.x0, box.y0, box.x1, box.y1)))
            else:
                continue

        # listすべて舐めて、表がオブジェクトとして閉じれてなければ閉じる
        # 列の終わりとかで、閉じていないケースがあるため
        if not o_x0 == 0.0:
            if line_num >= 3 and (abs(o_x1 - o_x0) > graph_min_size and abs(o_y0 - o_y1) > graph_min_size):
                # print("box3:\t", (o_x0, o_y0, o_x1, o_y1), line_num)
                table_list.append(LTTableRect(o_text, (o_x0, o_y0, o_x1, o_y1)))
            # else:
            #     print("not box3:", line_num)

        table_lists.append(table_list)
    return table_lists


# text groupを作る
def create_text_group_object(sort_lists):
    # text_group_lists = [[] for i in range(len(sort_lists))]
    text_group_lists = []
    # temp_num = 1
    for index, s_list in enumerate(sort_lists):
        text_group_list = []
        o_x0: float = 0.0
        o_y0: float = 0.0
        o_x1: float = 0.0
        o_y1: float = 0.0
        # flag = False
        for data in s_list:
            # print("aaaaaa:", (data.x0, data.y0, data.x1, data.y1), data.__class__.__name__)
            if not isinstance(data, LTTextBox):
                if data is s_list[-1] and o_x0 != 0.0:
                    # print("block3-1", (o_x0, o_y0, o_x1, o_y1))
                    text_group_list.append(LTTextBlock(None, (o_x0, o_y0, o_x1, o_y1)))
                continue
            # FIXME 注釈が、邪魔になるケースが多いのでブロック分けの際は無視している。
            # 今後、無視する単語リストとか作る必要があるかもしれない。
            if isinstance(data, LTTextBox) and (data.get_text() == "※\n" or data.get_text() == "※※\n"):
                # 8.pdfで、左列の最後が"※※"で終わっている
                if data is s_list[-1] and o_x0 != 0.0:
                    # print("block3-2", (o_x0, o_y0, o_x1, o_y1))
                    text_group_list.append(LTTextBlock(None, (o_x0, o_y0, o_x1, o_y1)))
                continue

            # 初回のLTTextBoxは値設定する
            if o_x0 == 0.0 and o_y0 == 0.0:
                o_x0, o_y0, o_x1, o_y1 = data.x0, data.y0, data.x1, data.y1
                # print("s0", (o_x0, o_y0, o_x1, o_y1))
                continue

            # 前のTextBoxの下部と次のTextBoxの上部が近いかどうか判定
            test1 = data.y1 - o_y0
            test2 = data.x0 - o_x0
            test3 = abs(data.y1 - o_y0) < line_margin2
            test4 = abs(data.x0 - o_x0) < title_center_range
            # print(o_y0, data.y1, test1, test2, test3, test4, data.get_text().strip().replace('\n', '').replace('\r', ''))
            if abs(data.y1 - o_y0) < line_margin2 and abs(data.x0 - o_x0) < title_center_range:
                # 距離が近いので、同じブロックとみなす
                o_x0 = min(data.x0, o_x0)
                o_y0 = min(data.y0, o_y0)
                o_x1 = max(data.x1, o_x1)
                o_y1 = max(data.y1, o_y1)
                # o_text += data.get_text()
                # flag = True
                # print("s1", (o_x0, o_y0, o_x1, o_y1))
            else:
                # if flag:
                # print("block1-s", (o_x0, o_y0, o_x1, o_y1))
                # o_text += data.get_text()
                text_group_list.append(LTTextBlock(None, (o_x0, o_y0, o_x1, o_y1)))
                # temp_num += 1
                o_x0, o_y0, o_x1, o_y1 = data.x0, data.y0, data.x1, data.y1
                # print("block1-e", (o_x0, o_y0, o_x1, o_y1))
                # flag = False

            if data is s_list[-1]:
                # if flag:
                #     print("block2", (o_x0, o_y0, o_x1, o_y1))
                #     o_text += data.get_text()
                text_group_list.append(LTTextBlock(None, (o_x0, o_y0, o_x1, o_y1)))
                # temp_num += 1

        text_group_lists.append(text_group_list)
    return text_group_lists


def create_block_object(table_lists, text_group_lists):
    block_lists = []
    temp_num = 1
    for index, t_list in enumerate(table_lists):
        block_list = []
        o_x0: float = 0.0
        o_y0: float = 0.0
        o_x1: float = 0.0
        o_y1: float = 0.0
        o_text = ""
        # flag = False
        temp_list = t_list
        temp_list.extend(text_group_lists[index])
        # 空リストの場合、飛ばす
        if not temp_list:
            block_lists.append(block_list)
            continue
        temp_list.sort(key=lambda b: -b.y1)
        for data in temp_list:
            test1 = o_x0 < data.x0 < o_x1
            test2 = o_x0 < data.x1 < o_x1
            test3 = data.x0 < o_x0 < data.x1
            test4 = data.x0 < o_x1 < data.x1
            test5 = o_y0 < data.y0 < o_y1
            test6 = o_y0 < data.y1 < o_y1
            test7 = data.y0 < o_y0 < data.y1
            test8 = data.y0 < o_y1 < data.y1
            test9 = o_y0 - data.y1
            test10 = o_y1 - data.y0
            if o_x0 == 0.0 and o_y0 == 0.0:
                o_x0 = data.x0
                o_y0 = data.y0
                o_x1 = data.x1
                o_y1 = data.y1
                # o_text = data.get_text()
                # fcd lag = True
                # print("s0", temp_num, (o_x0, o_y0, o_x1, o_y1))
            elif (
                    o_x0 < data.x0 < o_x1 or o_x0 < data.x1 < o_x1 or data.x0 < o_x0 < data.x1 or data.x0 < o_x1 < data.x1) \
                    and (
                    o_y0 < data.y0 < o_y1 or o_y0 < data.y1 < o_y1 or data.y0 < o_y0 < data.y1 or data.y0 < o_y1 < data.y1
                    or abs(o_y0 - data.y1) < line_margin2 or abs(o_y1 - data.y0) < line_margin2):
                # 距離が近いので、同じブロックとみなす
                o_x0 = min(data.x0, o_x0)
                o_y0 = min(data.y0, o_y0)
                o_x1 = max(data.x1, o_x1)
                o_y1 = max(data.y1, o_y1)
                # o_text += data.get_text()
                # flag = True
                # print("s1", temp_num, (o_x0, o_y0, o_x1, o_y1))
            else:
                # if flag:
                # print("block1", temp_num, (o_x0, o_y0, o_x1, o_y1))
                # o_text += data.get_text()
                block_list.append(LTBlock(o_text, (o_x0, o_y0, o_x1, o_y1)))
                temp_num += 1
                # else:
                #     block_list.append(LTBlock(0, (data.x0, data.y0, data.x1, data.y1)))
                #     temp_num += 1
                o_x0, o_y0, o_x1, o_y1 = data.x0, data.y0, data.x1, data.y1
                # o_text = data.get_text()
                # flag = False

            if data is t_list[-1]:
                # print("block2", temp_num, (o_x0, o_y0, o_x1, o_y1))
                # o_text += data.get_text()
                block_list.append(LTBlock(o_text, (o_x0, o_y0, o_x1, o_y1)))
                temp_num += 1

        block_lists.append(block_list)
    return block_lists


# TODO 多重リストにしているが、ここに来る前にまとめるべきか悩み中
def insert_text_in_block(sort_lists, block_lists):
    o_block_lists = []
    for index, b_list in enumerate(block_lists):
        block_list = []
        for b_data in b_list:
            o_text = ""
            for r_list in sort_lists:
                for r_data in r_list:
                    if not isinstance(r_data, LTTextBox):
                        continue
                    if b_data.x0 < r_data.x0 + acceptable_range + 10 \
                            and r_data.x1 < b_data.x1 + acceptable_range + 10 \
                            and b_data.y0 < r_data.y0 + acceptable_range \
                            and r_data.y1 < b_data.y1 + acceptable_range:
                        o_text += r_data.get_text()
            b_data.set_text(o_text)
            block_list.append(b_data)
        o_block_lists.append(block_list)
    return o_block_lists


# csvへ書き込み
# id, data, x0, x1, y0, y1
def write_body(writer, id, data, box, line_margin, indent, font_size, height):
    write_body_and_type(writer, id, "", data, box, line_margin, indent, font_size, height)


# 表などのtype情報も含めて書き込み
def write_body_and_type(writer, id, type, data, box, line_margin, indent, font_size, height):
    # if not data == "LTRect" and not data == "LTCurve" and not data == "LTLine":
    writer.writerow([id, type, data, box.x0, box.y0, box.x1, box.y1, line_margin, indent, font_size, height])
    # writer.writerow([data])


# 以下、調査用
# if data == "LTLine":
# if data == "LTRect":
# if data == "LTCurve":
# if type == "LTTableRect":
#     x_plot = [box.x0, box.x1, box.x1, box.x0, box.x0]
#     y_plot = [box.y0, box.y0, box.y1, box.y1, box.y0]
#     plt.plot(x_plot, y_plot)


def analyse_pdf_miner(writer, input_file_name):
    total_index = 0
    with open(input_file_name, 'rb') as f:
        # with open(sys.argv[1], 'rb') as f:
        for page_index, page in enumerate(PDFPage.get_pages(f)):
            # if page_index == 3:
            total_index = analyse_page(writer, input_file_name, total_index, page_index, page)


def analyse_page(writer, input_file_name, total_index, page_index, page):
    # 解析用の設定
    interpreter, device = analyze_setting()
    # ページを処理する。
    interpreter.process_page(page)
    # LTPageオブジェクトを取得。
    layout = device.get_result()

    # line_margin（y方向）,indent（x方向）を計算するための変数
    max_y = layout.height
    last_y = max_y
    start_x = 0
    last_x = start_x
    # layout size, height:841.8908   width:595.2751999999999　（真ん中：297.637）
    # x0：x始点、x1：x終点、yも同じ

    # ページ内の解析するオブジェクトのリストを取得する。
    boxes = find_object_recursively(layout)

    obj_list, block_list = create_block(boxes, layout.height, layout.width)

    name, ext = os.path.splitext(os.path.basename(input_file_name))
    img_lists = glob.glob(intermediate_dir + "/" + name + "_" + str(page_index) + ".png")
    out = cv2.imread(img_lists[0])  # 1つだけある想定
    d_png_h: float = out.shape[0] / layout.height
    d_png_w: float = out.shape[1] / layout.width
    # Table（表など）を表示、赤
    for index_table, data in enumerate(block_list):
        color = (0, 0, 255)
        if isinstance(data, LTTableRect):
            color = (255, 0, 255)
        cv2.rectangle(out, (int(data.x0 * d_png_w), int((layout.height - data.y0) * d_png_h)),
                      (int(data.x1 * d_png_w), int((layout.height - data.y1) * d_png_h)), color,
                      thickness=3)

    for ana_data in obj_list:
        # 調査用 ここから
        # if debug_flag_save_table \
        #         and (isinstance(ana_data, LTTableRect)
        #              or isinstance(ana_data, LTLine)
        #              or isinstance(ana_data, LTRect)
        #              or isinstance(ana_data, LTCurve)):
        #     write_body(writer, total_index, ana_data.__class__.__name__, ana_data, 0.0, 0.0, 0.0, "")
        #     total_index += 1
        #     # TODO LTLineでなく、LTCurveだけで、枠を成形しているPDFがある。表とか、一つの四角づつオブジェクトを持つ。。。
        #     if isinstance(ana_data, LTCurve):
        #         cv2.rectangle(out, (int(ana_data.x0 * d_png_w), int((layout.height - ana_data.y0) * d_png_h)),
        #                       (int(ana_data.x1 * d_png_w), int((layout.height - ana_data.y1) * d_png_h)), (0, 255, 255),
        #                       thickness=5)
        # 調査用 ここまで

        # LTTextBox、もしくは、LTBlockでもなければ次のオブジェクトに進む
        if not (isinstance(ana_data, LTTextBox) or isinstance(ana_data, LTBlock)):
            continue

        text = ana_data.get_text().strip()
        # text = text.replace('\n', '')
        # text = text.replace('\r', ' ')

        # LTBlockならば、csvに出力して次に進む
        if isinstance(ana_data, LTBlock):
            b_type = "block_"
            type = b_type + str(page_index)
            write_body_and_type(writer, total_index, type, ana_data.get_text().strip(), ana_data, last_y - ana_data.y1,
                                ana_data.x0 - last_x,
                                0, layout.height)
            last_y = ana_data.y0
            last_x = ana_data.x0
            total_index += 1
            continue

        # LTBlock以外は、LTTextBox。
        # fontサイズの取得。textの最初の文字について取得している
        font_size = 0.0
        for child in ana_data:
            for child2 in child:
                if isinstance(child2, LTChar):
                    font_size = child2.size
                    # print(data_index, child2.size, child2)
                    break

        flag = True
        # block内にある文章かどうかを確認して、block内の文章（LTTextBox）である場合、緑の枠で囲む
        for index, block_data in enumerate(block_list):
            # TODO 見た目上、表の中にあるのに解析上、表の外側にある場合がある。そのため、x軸の判定を強めにぼかしている
            if block_data.x0 < ana_data.x0 + acceptable_range + 10 \
                    and ana_data.x1 < block_data.x1 + acceptable_range + 10 \
                    and block_data.y0 < ana_data.y0 + acceptable_range \
                    and ana_data.y1 < block_data.y1 + acceptable_range \
                    and not isinstance(ana_data, LTBlock):
                flag = False
                cv2.rectangle(out, (int(ana_data.x0 * d_png_w), int((layout.height - ana_data.y0) * d_png_h)),
                              (int(ana_data.x1 * d_png_w), int((layout.height - ana_data.y1) * d_png_h)), (0, 255, 0),
                              thickness=2)
                break

        # block外の文章は、青枠で囲む
        if flag:
            write_body(writer, total_index, text, ana_data, last_y - ana_data.y1, ana_data.x0 - last_x, font_size,
                       layout.height)
            cv2.rectangle(out, (int(ana_data.x0 * d_png_w), int((layout.height - ana_data.y0) * d_png_h)),
                          (int(ana_data.x1 * d_png_w), int((layout.height - ana_data.y1) * d_png_h)), (255, 0, 0),
                          thickness=2)
            last_y = ana_data.y0
            last_x = ana_data.x0
            total_index += 1

    # ページが変わるタイミングで、保存
    # plt.xlim([0, layout.width])
    # plt.ylim([0, layout.height])
    # plt.savefig(output_img_name(page_index))
    # plt.clf()

    output_img_file_name = output_image_dir + "/" + os.path.basename(img_lists[0])
    cv2.imwrite(output_img_file_name, out)

    return total_index


def output_file_name(input_file_name):
    name, ext = os.path.splitext(os.path.basename(input_file_name))
    return output_dir + "/res_" + name + ".csv"


def start_analyse(input_file_name):
    # 出力用のテキストファイル
    # windowsで出力するときエンコードエラーがでるのでencoding="utf-8_sig"を追加
    with open(output_file_name(input_file_name), 'w', newline='', encoding="utf-8_sig") as output_txt:
        writer = csv.writer(output_txt, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        # 解析結果を格納するcsvファイルのヘッダを書き出す
        writer.writerow(
            ["id", "type", "data", "x0", "y0(lower)", "x1", "y1(upper)", "line_margin", "indent", "font_size", "word"])

        # ファイルの書き出しが複数メソッドにわたっている、かつ、このメソッド内で別のopenをしていたりと、もう少し工夫したい。
        analyse_pdf_miner(writer, input_file_name)

    plt.close()


if __name__ == '__main__':
    # 新規で行う場合は、結果フォルダを空にする
    output_setting()

    pdf_lists = glob.glob(input_pdf_dir + "/*.pdf")
    # pdf_lists = glob.glob(input_pdf_dir + "/isv01lpd.pdf")
    for file_name in pdf_lists:
        start_analyse(file_name)
