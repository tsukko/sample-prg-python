import math
import os
import re
import shutil
import sys
from collections import defaultdict

import openpyxl
from openpyxl.styles.borders import Border, Side
import pandas as pd
from pdfminer.layout import LTContainer, LTTextBox, LTImage, LTLine, LTRect, LTCurve
from table import LTTableRect, LTAnswerBlock, LTInquiryBlock

'''パラメータ　ここから'''
input_pdf_dir = "input"
output_dir = "output_pmn"
output_image_dir = output_dir + "/img"
output_img_tbl_dir = output_dir + "/fig_tbl"
output_xlsx_dir = output_dir + "/xlsx_tbl"
intermediate_dir = "Intermediate_img"
# 見た目は線は表の内側にあるのに、座標は外側を示しているケースがあり、
# 誤差とみなして判断するための値
# 右列のLTTextBoxのx座標が結構ぶれる（左列の座標に入ったり）ので、許容範囲を設定する
acceptable_range_x: float = 18.0
acceptable_range_y: float = 18.0
acceptable_range_inquiry: float = 0.3
# LTRectで、グラフなどを示す。小さな図形などを拾いまくるので、最小サイズを設定する
graph_min_size: float = 15.0
'''パラメータ　ここまで'''

header_obj = []
table_index = 0

# TODO クラス化したい
save_file_name = None


def output_setting():
    """
    結果の出力用ディレクトリが存在していれば、クリアして再生成する
    :return:
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(output_dir)
    os.makedirs(output_image_dir)
    os.makedirs(output_img_tbl_dir)
    os.makedirs(output_xlsx_dir)


# 再帰的なオブジェクトから子オブジェクトを抽出してリスト化する
def find_object_recursively(layout_obj):
    """
    再帰的なオブジェクトから子オブジェクトを抽出してリスト化する
    :param layout_obj:
    :return:
    """
    # LTTextBoxを継承するオブジェクトの場合は1要素のリストを返す。
    if isinstance(layout_obj, LTTextBox) and layout_obj.get_text() != ' \n':
        return [layout_obj]

    if isinstance(layout_obj, LTImage):
        return [layout_obj]

    # 表や枠となりうるオブジェクト
    if isinstance(layout_obj, LTLine):
        return [layout_obj]
    if isinstance(layout_obj, LTRect):
        # print(layout_obj)
        return [layout_obj]
    # LTLine も LTRect も、LTCurve を継承しているので、これで両方とも返る
    # if isinstance(layout_obj, LTCurve):
    #     return [layout_obj]

    # LTPageやLTFigureなど、LTContainerを継承するオブジェクトは子要素を含むので、再帰的に探す。
    if isinstance(layout_obj, LTContainer):
        boxes = []
        for child_con in layout_obj:
            boxes.extend(find_object_recursively(child_con))

        return boxes

    # print("none object:", layout_obj.__class__.__name__)
    return []  # その他の場合は空リストを返す。


def save_image(img_data):
    """
    画像ファイルを保存する
    :param img_data:
    :return:
    """
    # print(r_data.name, r_data.stream)
    # print(r_data.stream.get_filters())
    b = img_data.stream.rawdata
    ext = ""
    # 参考。jpgでは確認済み
    # https://qiita.com/HayaoSuzuki/items/ddeceb60037644734868
    if re.match(br"^\xff\xd8", b[:2]):
        ext = "jpg"
    elif re.match(br"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", b[:8]):
        ext = "png"
    elif re.match(b"^\x47\x49\x46\x38", b[:4]):
        ext = "gif"
    else:
        ext = "img"

    f = open(output_image_dir + "/" + img_data.name + "." + ext, "bw")
    f.write(img_data.stream.rawdata)


def update_coordinates(org_bbox, com_box):
    return min(org_bbox[0], com_box[0]), min(org_bbox[1], com_box[1]), max(org_bbox[2], com_box[2]), \
           max(org_bbox[3], com_box[3])


def combining_sentences(sort_list, inquiry_list):
    """
    照会事項：table_listの座標内の文字列を結合する
    回答：上記以外の文字列を結合する
    ここで返るblock_listは、LTInquiryBlockかLTTextBlockのどちらかのみ
    :param sort_list:
    :param inquiry_list:
    :return: 照会事項と回答のリスト
    """
    block_list = []
    inquiry_index = 0

    if len(inquiry_list) == 0:
        inquiry_obj = LTInquiryBlock("", (0.0, 0.0, 0.0, 0.0))
    else:
        inquiry_obj = inquiry_list[inquiry_index]

    inquiry_text = ""
    answer_text = ""
    table_y0 = float('inf')
    table_y1 = float('inf')
    table_text_raw = ""
    lo_x0, lo_y0, lo_x1, lo_y1 = 0.0, 0.0, 0.0, 0.0
    # print("start create block.")
    for r_data in sort_list:
        if isinstance(r_data, LTImage):
            # 画像イメージは
            if math.isclose(lo_x0, 0.0):
                # print("6: first:", r_data)
                (lo_x0, lo_y0, lo_x1, lo_y1) = r_data.bbox
            lo_x0, lo_y0, lo_x1, lo_y1 = update_coordinates(r_data.bbox, (lo_x0, lo_y0, lo_x1, lo_y1))
            answer_text += "[img_s:dummy:img_e]\n"
            # ここでは保存しない
            # save_image(r_data)
            # print("6: first:", r_data)
            block_list.append(r_data)
        elif isinstance(r_data, LTTableRect):
            if math.isclose(lo_x0, 0.0):
                # print("7: first:", r_data)
                (lo_x0, lo_y0, lo_x1, lo_y1) = r_data.bbox
            lo_x0, lo_y0, lo_x1, lo_y1 = update_coordinates(r_data.bbox, (lo_x0, lo_y0, lo_x1, lo_y1))
            table_y0 = r_data.y0
            # print("7: first:", r_data)
            block_list.append(r_data)
        elif not isinstance(r_data, LTTextBox):
            # print("debug:", r_data)
            pass
        else:
            # print("0:", r_data.get_text().replace('\n', '').replace('\r', ''),
            #       r_data.y0, r_data.y1, inquiry_obj.y0, inquiry_obj.y1)
            # 照会事項の枠の座標より内側ならば、照会事項の文とみなす
            if inquiry_obj.x0 < r_data.x0 + acceptable_range_inquiry \
                    and r_data.x1 < inquiry_obj.x1 + acceptable_range_inquiry \
                    and inquiry_obj.y0 < r_data.y0 + acceptable_range_inquiry \
                    and r_data.y1 < inquiry_obj.y1 + acceptable_range_inquiry:
                # print("1-1: add inquiry:", r_data, inquiry_obj)
                # ここはLTInquiryBlockの中。すでに回答Textにデータがある場合は、それまでの回答をブロックとしてまとめる
                if answer_text:
                    # print("1-2: answer_text", answer_text, lo_x0, lo_y0, lo_x1, lo_y1)
                    if table_text_raw:

                        answer_text += table_text_raw + ":tbl_e]\n"
                        table_text_raw = ""
                    block_list.append(LTAnswerBlock(answer_text, (lo_x0, lo_y0, lo_x1, lo_y1), None))
                    answer_text = ""
                    lo_x0, lo_y0, lo_x1, lo_y1 = 0.0, 0.0, 0.0, 0.0

                inquiry_text += r_data.get_text()
            else:
                # 照会事項の枠より、Textが下の方に来たら、回答の文とみなす
                if r_data.y1 < inquiry_obj.y0 and inquiry_obj is not inquiry_list[-1]:
                    # print("2-1: next:", inquiry_text, inquiry_obj)
                    block_list.append(LTInquiryBlock(inquiry_text, inquiry_obj.bbox))
                    inquiry_index += 1
                    inquiry_obj = inquiry_list[inquiry_index]
                    inquiry_text = ""

                # print("2-2 :add answer:", r_data, inquiry_obj)
                if math.isclose(lo_x0, 0.0):
                    # print("2-3: first:", r_data)
                    (lo_x0, lo_y0, lo_x1, lo_y1) = r_data.bbox
                lo_x0, lo_y0, lo_x1, lo_y1 = update_coordinates(r_data.bbox, (lo_x0, lo_y0, lo_x1, lo_y1))

                if table_y0 < r_data.y0:
                    # 表の中の文章
                    # print("log0:表の中の文章: ", table_y0, table_y1, r_data)
                    if table_text_raw:
                        table_text_raw += r_data.get_text()
                    else:
                        table_text_raw = "[tbl_s:" + r_data.get_text()
                else:
                    # 表の外の文章
                    if table_text_raw:
                        answer_text += table_text_raw + ":tbl_e]\n"
                        table_text_raw = ""
                    answer_text += r_data.get_text()

        if r_data is sort_list[-1]:
            # print("3: r_data is sort_list[-1]:", r_data)
            if inquiry_text:
                # print("3-1: add inquiry_text:", inquiry_obj.bbox)
                block_list.append(LTInquiryBlock(inquiry_text, inquiry_obj.bbox))
            if answer_text or table_text_raw:
                # print("3-2: add answer_text:", (lo_x0, lo_y0, lo_x1, lo_y1))
                if table_text_raw:
                    answer_text += table_text_raw + ":tbl_e]\n"
                block_list.append(LTAnswerBlock(answer_text, (lo_x0, lo_y0, lo_x1, lo_y1), None))
        # else:
        #     print("3-4", r_data, sort_list[-1])
    # print("last:", len(block_list), block_list)
    return block_list


def create_table_object(sort_list, is_after_second_page, min_x, max_x):
    """
    Line、Rectオブジェクトから、照会事項の枠と表オブジェクトを作る
    # 注意！　y座標は、y1が上
    :param sort_list:
    :param is_after_second_page:
    :param min_x:
    :param max_x:
    :return:
    """
    table_list = []
    inquiry_list = []
    line_num: int = 0
    lo_x0, lo_y0, lo_x1, lo_y1 = 0.0, 0.0, 0.0, 0.0
    lo_text = ""
    for box in sort_list:
        if isinstance(box, (LTRect, LTLine)):
            # print("0:\t", lo_x0, lo_y0, lo_x1, lo_y1, line_num, box)
            if lo_x0 == 0.0 and lo_y0 == 0.0:
                # 1. 最初のLine位置を定義
                lo_x0, lo_y0, lo_x1, lo_y1, line_num = box.x0, box.y0, box.x1, box.y1, line_num + 1
                # print("1-1:\t", lo_x0, lo_y0, lo_x1, lo_y1, line_num)
            else:
                # デバッグしやすいようにif文の分岐を分けている
                # 比較Line座標（box）と、枠候補座標（lo_～）を比較する。
                # y座標のどちらかがほぼ同じ値で、かつ、比較Line座標のx始点が、枠候補のx座標内　の場合か、
                # もしくは、比較Lineのy座標が、どちらも、枠候補のy座標内なら同じ枠とみなす。
                if ((abs(box.y0 - lo_y0) < acceptable_range_y or abs(box.y1 - lo_y1) < acceptable_range_y)
                    and lo_x0 - acceptable_range_x < box.x0 < lo_x1 + acceptable_range_x) \
                        or (lo_y0 < box.y0 < lo_y1 and lo_y0 < box.y1 < lo_y1):
                    lo_x0, lo_y0, lo_x1, lo_y1 = update_coordinates(box.bbox, (lo_x0, lo_y0, lo_x1, lo_y1))
                    line_num += 1
                    # print("2-1:\t", lo_x0, lo_y0, lo_x1, lo_y1, line_num, box)

                elif (abs(lo_x0 - box.x0) < acceptable_range_x or abs(lo_x1 - box.x1) < acceptable_range_x
                      or (lo_x0 < box.x0 < lo_x1 and lo_x0 < box.x1 < lo_x1)) \
                        and abs(box.y1 - lo_y0) < acceptable_range_y:
                    # 比較Lineのx座標のどちらかが、枠候補とほぼ同じ値、もしくは、どちらのx座標も枠候補内であり、
                    # かつ、下の方のy座標と比較Lineの上の方の座標がほぼ同じ場合、同じ枠とみなす。
                    lo_x0, lo_y0, lo_x1, lo_y1 = update_coordinates(box.bbox, (lo_x0, lo_y0, lo_x1, lo_y1))
                    line_num += 1
                    # print("2-2:\t", lo_x0, lo_y0, lo_x1, lo_y1, line_num, box)
                elif abs(lo_y0 - box.y0) < acceptable_range_y and abs(lo_y1 - box.y1) < acceptable_range_y:
                    # 照会事項がページ跨ぎで、くると、四角枠の上部の線がないため、両端の上下のy座標を比較して同じならば、
                    # 照会事項の枠とみなすようにする
                    lo_x0, lo_y0, lo_x1, lo_y1 = update_coordinates(box.bbox, (lo_x0, lo_y0, lo_x1, lo_y1))
                    line_num += 1
                    # print("2-3:\t", lo_x0, lo_y0, lo_x1, lo_y1, line_num, box)
                else:
                    # 表の終わり？
                    if line_num >= 4 and (abs(lo_x1 - lo_x0) > graph_min_size and abs(lo_y0 - lo_y1) > graph_min_size):
                        # print("box1:\t", (lo_x0, lo_y0, lo_x1, lo_y1), line_num, min_x - lo_x0, max_x - lo_x1)
                        # 表かどうかの判定は厳しめにする
                        if (abs(min_x - lo_x0) > acceptable_range_inquiry or
                            abs(max_x - lo_x1) > acceptable_range_inquiry) \
                                and is_after_second_page:
                            # TODO ここのis_after_second_pageは必要かどうか確認
                            table_list.append(LTTableRect(lo_text, (lo_x0, lo_y0, lo_x1, lo_y1)))
                        else:
                            inquiry_list.append(LTInquiryBlock(lo_text, (lo_x0, lo_y0, lo_x1, lo_y1)))
                    if box.y1 - box.y0 > 800:
                        # FIXME 15.pdfのように左端に大きな縦線がある場合に無視する。値は苦し紛れ
                        lo_x0, lo_y0, lo_x1, lo_y1, line_num = 0.0, 0.0, 0.0, 0.0, 0
                    else:
                        lo_x0, lo_y0, lo_x1, lo_y1, lo_text, line_num = box.x0, box.y0, box.x1, box.y1, "", 1
                    # print("1-2:\t", lo_x0, lo_y0, lo_x1, lo_y1, line_num)
        elif isinstance(box, LTTextBox):
            # 直前に、Lineがなかった場合(tmpX0 == 0.0)は、表でないので次に行く
            if lo_x0 == 0.0:
                continue
            # Lineがあった状態で、TextBoxが来た場合、Textのx座標がLine内にあると、次に行く
            elif lo_x0 - acceptable_range_x < box.x0 < lo_x1 + acceptable_range_x \
                    and lo_x0 - acceptable_range_x < box.x1 < lo_x1 + acceptable_range_x:
                # print("4:\t", box.get_text().replace('\n', '').replace('\r', ''), box,
                #       lo_x0, lo_y0, lo_x1, lo_y1, line_num)
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
    if not lo_x0 == 0.0:
        # print("aaa", (lo_x0, lo_y0, lo_x1, lo_y1), abs(lo_x1 - lo_x0), abs(lo_y0 - lo_y1))
        if line_num >= 3 and (abs(lo_x1 - lo_x0) > graph_min_size and abs(lo_y0 - lo_y1) > graph_min_size):
            # print("box3:\t", (lo_x0, lo_y0, lo_x1, lo_y1), line_num, min_x - lo_x0, max_x - lo_x1)
            if (abs(min_x - lo_x0) > acceptable_range_inquiry or abs(max_x - lo_x1) > acceptable_range_inquiry) and \
                    is_after_second_page:
                # TODO ここのis_after_second_pageは必要かどうか確認
                table_list.append(LTTableRect(lo_text, (lo_x0, lo_y0, lo_x1, lo_y1)))
            else:
                inquiry_list.append(LTInquiryBlock(lo_text, (lo_x0, lo_y0, lo_x1, lo_y1)))
        # else:
        #     print("not box3:", line_num)

    # print("end table_list:", table_list)
    return inquiry_list, table_list


def is_ignore_obj(obj, min_x, max_x):
    """
    ヘッダ、フッタ、サイドの文字領域を無視するための判定処理
    :param obj:
    :param min_x:
    :param max_x:
    :return:
    """
    # この判定は緩め
    conditions_side_l = obj.x0 < min_x - acceptable_range_x
    conditions_side_r = max_x + acceptable_range_x < obj.x1
    # print(obj.x0, obj.x1, min_x, max_x, obj.x0 < min_x, max_x < obj.x1)
    return conditions_side_l or conditions_side_r


def sort_and_ignore_object(object_list, min_x, max_x):
    """
    オブジェクトを並び替える
    :param object_list:
    :param min_x:
    :param max_x:
    :return:
    """
    temp_lists = []
    # 最初にy方向でsort
    # テキストボックスの左上の座標の順でテキストボックスをソートする。
    # y1（Y座標の値）は上に行くほど大きくなるので、正負を反転させてソートしている（降順）。
    # 見た目的に、y1が上側、 y0が下側
    object_list.sort(key=lambda b: (-b.y1, b.x0))

    # print("sort_object1", len(object_list))
    for obj in object_list:

        # LTLineだと拾えないケースがあった
        if isinstance(obj, LTCurve):
            # if isinstance(obj, LTLine) or isinstance(obj, LTRect):
            if obj.x0 < 0:
                # マイナス座標のxが存在する
                continue
        if is_ignore_obj(obj, min_x, max_x):
            # if isinstance(obj, LTTextBox):
            #     print("deeeefefe", obj)
            continue
        # 同じLTLineの場合無視する。

        if temp_lists and isinstance(temp_lists[-1], (LTRect, LTLine)) and isinstance(obj, (LTRect, LTLine)):
            if temp_lists[-1].bbox == obj.bbox:
                # print("ignore line.")
                continue

        # print("sort_object:", obj)
        temp_lists.append(obj)

    return temp_lists


def create_block(object_list, height, width, is_after_second_page, min_x, max_x, exclude_header, exclude_footer):
    """
    オブジェクトを並び替えてたりして、ブロックをつくる
    :param exclude_footer:
    :param exclude_header:
    :param max_x:
    :param min_x:
    :param is_after_second_page:
    :param object_list:
    :param height:
    :param width:
    :return:
    """
    global header_obj
    if width < height:
        # 縦ページ
        # ヘッダ、フッタ情報も入ったまま返してもらう
        sort_list_include_header_footer = sort_and_ignore_object(object_list, min_x, max_x)
        sort_list = sort_list_include_header_footer[exclude_header:-exclude_footer]
        if not is_after_second_page:
            # 最初の照会事項のページでない場合、ヘッダを登録する
            header_obj = sort_list_include_header_footer[:exclude_header]
        # print("header_str1: ", first_inquiry, header_obj, exclude_header, width, height)
    else:
        # 横ページ
        # ヘッダが存在する前提で処理が行われる
        header_str = "文書名 「～～～～～～～～～」 \n" if not header_obj else header_obj[0].get_text()
        # print("header_str2: ", header_obj, width , height)
        # ヘッダ文字列と同じ文字列があるオブジェクトを検索する
        header_obj_land = [s for s in object_list if isinstance(s, LTTextBox) and header_str in s.get_text()]
        # 横ページで、ヘッダが存在しないケースもある
        if header_obj_land:
            min_x = header_obj_land[0].x0
            sort_list_include_header_footer = sort_and_ignore_object(object_list, min_x, width)
            # ヘッダ、フッタを取り除く
            sort_list = sort_list_include_header_footer[exclude_header:-exclude_footer]
        else:
            # 横ページでヘッダがないケースでは、リストの最初のx0座標を使う
            # TODO サイドの文字列が長い場合、x0座標が想定されない値になってしまう
            # TODO ヘッダなしだけを考えていて、フッタなしは考慮していない
            min_x = object_list[0].x0
            sort_list = sort_and_ignore_object(object_list, min_x, width)

    # 表の抽出とTextグループの計算（一つのメソッドでまとめられるが、わかりやすさのために現状は分けている）
    inquiry_list, table_list = create_table_object(sort_list, is_after_second_page, min_x, max_x)

    sort_list.extend(table_list)
    sort_list.sort(key=lambda b: (-b.y1, b.x0))

    block_list = combining_sentences(sort_list, inquiry_list)

    return block_list


### ここから、最初の照会事項を取得してそのx座標を算出するための処理
###　このx座標を見て、サイドの不要な文字を無視する
def find_object_lines(layout_obj):
    # 表や枠となりうるオブジェクト

    if isinstance(layout_obj, LTLine):
        # print("LTLine:", layout_obj)
        return [layout_obj]
    if isinstance(layout_obj, LTRect):
        # print("LTRect",layout_obj)
        return [layout_obj]
    # LTLine も LTRect も、LTCurve を継承しているので、これで両方とも返る
    # if isinstance(layout_obj, LTCurve):
    #     return [layout_obj]

    # LTPageやLTFigureなど、LTContainerを継承するオブジェクトは子要素を含むので、再帰的に探す。
    # if isinstance(layout_obj, LTPage):
    if isinstance(layout_obj, LTContainer):
        boxes = []
        for child_con in layout_obj:
            # print("yyyy",child_con )
            boxes.extend(find_object_lines(child_con))

        # print("pppp",boxes)
        return boxes

    # print("none object:", layout_obj.__class__.__name__)
    return []  # その他の場合は空リストを返す。


def get_first_inquiry_x_pos(boxes):
    line_num: int = 0
    lo_x0, lo_y0, lo_x1, lo_y1 = -1.0, 0.0, -1.0, 0.0

    for box in boxes:
        if lo_x0 == 0.0 and lo_y0 == 0.0:
            # 1. 最初のLine位置を定義
            lo_x0, lo_y0, lo_x1, lo_y1, line_num = box.x0, box.y0, box.x1, box.y1, line_num + 1
            # print("1-1:\t", o_x0, o_y0, o_x1, o_y1, line_num)
        else:
            # デバッグしやすいようにif文の分岐を分けている
            # y座標がほぼ同じなら同じ表とみなし、x終点を変更
            # Lineの始点が同じ場合、表の下部の線と想定
            if ((abs(box.y0 - lo_y0) < acceptable_range_y or abs(box.y1 - lo_y1) < acceptable_range_y)
                and lo_x0 - acceptable_range_x < box.x0 < lo_x1 + acceptable_range_x) \
                    or (lo_y0 < box.y0 < lo_y1 and lo_y0 < box.y1 < lo_y1):
                lo_x0, lo_y0, lo_x1, lo_y1 = update_coordinates(box.bbox, (lo_x0, lo_y0, lo_x1, lo_y1))
                line_num += 1
                # print("2-1:\t", o_x0, o_y0, o_x1, o_y1, line_num, box)
            elif (abs(lo_x0 - box.x0) < acceptable_range_x or abs(lo_x1 - box.x1) < acceptable_range_x
                  or (lo_x0 < box.x0 < lo_x1 and lo_x0 < box.x1 < lo_x1)) \
                    and abs(box.y1 - lo_y0) < acceptable_range_y:
                # 上のy0、y1で一致しなかった場合、
                lo_x0, lo_y0, lo_x1, lo_y1 = update_coordinates(box.bbox, (lo_x0, lo_y0, lo_x1, lo_y1))
                line_num += 1
                # print("2-2:\t", o_x0, o_y0, o_x1, o_y1, line_num, box)
            elif abs(lo_y0 - box.y0) < acceptable_range_y and abs(lo_y1 - box.y1) < acceptable_range_y:
                # 照会事項がページ跨ぎで、くると、四角枠の上部の線がないため、両端の上下のy座標を比較して同じならば、
                # 照会事項とみなすようにする
                lo_x0, lo_y0, lo_x1, lo_y1 = update_coordinates(box.bbox, (lo_x0, lo_y0, lo_x1, lo_y1))
                line_num += 1
                # print("2-3:\t", o_x0, o_y0, o_x1, o_y1, line_num, box)
            else:
                # 表の終わり？
                if line_num >= 4 and (abs(lo_x1 - lo_x0) > graph_min_size and abs(lo_y0 - lo_y1) > graph_min_size):
                    # print("box1:\t", (o_x0, o_y0, o_x1, o_y1), line_num, minX0 - o_x0, maxX1 - o_x1)
                    # table_list.append(LTInquiryBlock(lo_text, (lo_x0, lo_y0, lo_x1, lo_y1)))
                    return lo_x0, lo_x1
                if box.y1 - box.y0 > 800:
                    # FIXME 15.pdfのように左端に大きな縦線がある場合に無視する。値は苦し紛れ
                    lo_x0, lo_y0, lo_x1, lo_y1, line_num = 0.0, 0.0, 0.0, 0.0, 0
                else:
                    lo_x0, lo_y0, lo_x1, lo_y1, line_num = box.x0, box.y0, box.x1, box.y1, 1
                # print("1-2:\t", o_x0, o_y0, o_x1, o_y1, line_num)

    if not lo_x0 == 0.0:
        # print("aaa", (o_x0, o_y0, o_x1, o_y1),abs(o_x1 - o_x0),   abs(o_y0 - o_y1) )
        if line_num >= 3 and (abs(lo_x1 - lo_x0) > graph_min_size and abs(lo_y0 - lo_y1) > graph_min_size):
            # print("box3:\t", (o_x0, o_y0, o_x1, o_y1), line_num, minX0 - o_x0, maxX1 - o_x1)
            # table_list.append(LTInquiryBlock(lo_text, (lo_x0, lo_y0, lo_x1, lo_y1)))
            return lo_x0, lo_x1

    return lo_x0, lo_x1
