import os.path
import glob
from pdf2image import convert_from_path

'''パラメータ　ここから'''
output_image_dir = "Intermediate_img"
input_pdf_dir = "input"
param_dpi = 600
'''パラメータ　ここまで'''


# 結果の出力用ディレクトリが存在しなければ、生成する
def output_setting():
    if not os.path.exists(output_image_dir):
        os.makedirs(output_image_dir)


# PDFを画像に変換する
def exchange_pdf_to_image(pdf_file_name):
    images = convert_from_path(pdf_file_name, dpi=param_dpi)
    output_setting()
    name, ext = os.path.splitext(os.path.basename(pdf_file_name))
    for index, image in enumerate(images):
        # isv01lpd.pdf の場合、isv01lpd_400_0.png
        split_image_name = output_image_dir + '/' + name + '_' + str(param_dpi) + '_' + str(index) + '.png'
        image.save(split_image_name, 'png')
    return images


# PDFファイルが格納されたディレクトリからPDFリストを抽出して、各ファイルを変換関数に渡す
def exchange_pdf_list_to_images():
    pdf_list = glob.glob(input_pdf_dir + "/*.pdf")
    for file_name in pdf_list:
        exchange_pdf_to_image(file_name)


exchange_pdf_list_to_images()
