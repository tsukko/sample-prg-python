import sys
import os.path
from PIL import Image
import pyocr
import pyocr.builders
import glob
import shutil
import cv2
from pdf2image import convert_from_path

import matplotlib.pyplot as plt

'''
tesseractの試作

解析するときのBuilderによって、結果が違う。
LineBoxBuilderが行単位で判定できるので、今回のニーズに一番マッチしている。
raw text : TextBuilder
words + boxes : WordBoxBuilder
lines + words + boxes : LineBoxBuilder

https://github.com/tesseract-ocr/tesseract
ページセグメンテーションモード (PSM)
※公式情報が拾えていない
0 文字方向および書字系の検出 (Orientation and script detection: OSD) のみ
1 自動ページセグメンテーション（OSDありでOCR）.
2 自動ページセグメンテーション（OSDなし）
3 完全自動ページセグメンテーション（OSDなし） (Default)
4 単一カラムの様々なサイズのテキストとみなす
5 垂直方向に整列した単一カラムの均一ブロックテキストとみなす
6 単一カラムの均一ブロックテキストとみなす
7 画像を単一行のテキストとして扱う
8 画像を単語1つのみ含まれるものとして扱う
9 画像を円で囲まれた単語1つのみを含むものとして扱う
10 画像を1文字のだけが含まれるものとして扱う
11 Sparse text: 不特定の順序でできるだけ多くのテキストを探す
12 Sparse text: OSDあり
13 Raw line: 内部の処理をバイパスしつつ画像内にテキストが1行だけあるものとして扱う
'''
'''パラメータ　ここから'''
output_dir = "output_tes"
output_image_dir = output_dir + "/output_img"
input_image_dir = "Intermediate_img"
'''パラメータ　ここまで'''

# tesseract周りの設定（別途Windows側でtesseractインストールなどの設定する必要あり）
tools = pyocr.get_available_tools()
if len(tools) == 0:
    print("No OCR tool found")
    sys.exit(1)
# The tools are returned in the recommended order of usage
tool = tools[0]
print("Will use tool '%s'" % (tool.get_name()))
langs = tool.get_available_languages()
print("Available languages: %s" % ", ".join(langs))
lang = langs[2]
print("Will use lang '%s'" % (lang))


# 結果の出力用ディレクトリが存在していれば、クリアして再生成する
def output_setting():
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    if os.path.exists(output_image_dir):
        shutil.rmtree(output_image_dir)

    os.makedirs(output_dir)
    os.makedirs(output_image_dir)


##### 1. TextBuilderの取得
# builder = pyocr.builders.TextBuilder(tesseract_layout=4, cuneiform_dotmatrix=True,
#                 cuneiform_fax=True, cuneiform_singlecolumn=True)
# txt = tool.image_to_string(Image.open('test.png'),
#                                 lang=lang,
#                                 builder=builder)
# with open("result2.txt", 'w', encoding='utf-8') as file_descriptor:
#     builder.write_file(file_descriptor, txt)

##### 2. WordBoxBuilderの取得
# builderW = pyocr.builders.WordBoxBuilder(tesseract_layout=4)
# word_box = tool.image_to_string(Image.open('test.png'),
#                                 lang=lang,
#                                 builder=builderW)
#
# with open("resultw.txt", 'w', encoding='utf-8') as file_descriptor_w:
#     builderW.write_file(file_descriptor_w, word_box)


##### LineBoxBuilderの取得　★これがよさげ
def analyse_image_to_line(image_file, index):
    builder_line = pyocr.builders.LineBoxBuilder()
    box_lines = tool.image_to_string(Image.open(image_file),
                                     lang=lang,
                                     builder=builder_line)
    # 結果を保存（HTML形式）
    name, ext = os.path.splitext(os.path.basename(image_file))
    name_slice = name[0:len(name) - 2]
    save_res = output_dir + "/res_tes_line_" + name + ".txt"
    with open(save_res, 'w', encoding='utf-8') as file_descriptor_line:
        builder_line.write_file(file_descriptor_line, box_lines)

    save_text = output_dir + "/res_tes_text_" + name_slice + ".txt"
    with open(save_text, 'a', encoding='utf-8') as file_descriptor_text:
        for line in box_lines:
            file_descriptor_text.write(line.content + "\r")
        file_descriptor_text.write("-----------\r")

    out = cv2.imread(image_file)
    for line in box_lines:
        cv2.rectangle(out, line.position[0], line.position[1], (0, 255, 0), 5)
    # こちらの方法だと、ひとオブジェクト毎に色が変わるため、判別しやすい
    #     x_plot = [l.position[0][0], l.position[1][0], l.position[1][0], l.position[0][0], l.position[0][0]]
    #     y_plot = [l.position[0][1], l.position[0][1], l.position[1][1], l.position[1][1], l.position[0][1]]
    #     plt.plot(x_plot, y_plot)
    #
    # plt.savefig("line_box.png")
    # plt.clf()

    output_img_name = output_image_dir + "/" + os.path.basename(image_file)
    cv2.imwrite(output_img_name, out)


if __name__ == '__main__':
    output_setting()
    image_list = glob.glob(input_image_dir + "/*.png")
    for index, img_file_name in enumerate(image_list):
        analyse_image_to_line(img_file_name, index)
