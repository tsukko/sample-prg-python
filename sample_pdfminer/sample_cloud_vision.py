import cv2
import glob
import io
import os
import shutil
from google.cloud import vision
from google.cloud.vision import types

from PIL import Image, ImageDraw
from google.cloud.vision_v1 import ImageAnnotatorClient
from google.cloud.vision_v1.proto.image_annotator_pb2 import AnnotateImageResponse, AnnotateImageRequest

'''パラメータ　ここから'''
output_dir = "output_gcv"
output_image_dir = output_dir + "/output_img"
input_image_dir = "Intermediate_img"
'''パラメータ　ここまで'''

# import gpyocr

# # text, conf = gpyocr.tesseract_ocr('test.png', lang='jpn', psm=6)
# # print(text)
# aaa, confidence = gpyocr.google_vision_ocr('test.png', langs=['ja'])


# 結果の出力用ディレクトリが存在していれば、クリアして再生成する
def output_setting():
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    if os.path.exists(output_image_dir):
        shutil.rmtree(output_image_dir)

    os.makedirs(output_dir)
    os.makedirs(output_image_dir)


# cloud vision apiを使って、
def get_page_document(file_name):
    with io.open(file_name, 'rb') as image_file:
        content = image_file.read()

    image = types.Image(content=content)
    # 日本語のヒントを与える
    # image_context = types.ImageContext(language_hints=['ja'])

    response: AnnotateImageResponse = client.document_text_detection(image=image)
    # response = client.annotate_image({
    #     'image': {'content': content},
    #     'features': [{
    #         'type': vision.enums.Feature.Type.DOCUMENT_TEXT_DETECTION
    #     }],
    #     'image_context': {'language_hints': ['jp']}
    # })

    name, ext = os.path.splitext(os.path.basename(file_name))
    name_slice = name[0:len(name) - 2]
    # 別ページのテキストも一つのファイルにすべてまとめる
    with open(output_dir + "/res_gcv_text_" + name_slice + ".txt", 'a', encoding='utf-8') as file_descriptor_txt:
        file_descriptor_txt.write(response.full_text_annotation.text)
        file_descriptor_txt.write("-----------\r")

    # 各ページごとにjson形式のデータを出力する
    with open(output_dir + "/res_gcv_json_" + name + ".txt", 'w', encoding='utf-8') as file_descriptor_json:
        file_descriptor_json.write(str(response.full_text_annotation))

    doc: AnnotateImageResponse.full_text_annotation = response.full_text_annotation
    return doc


def analyze_document(file_name):
    out = cv2.imread(file_name)
    doc = get_page_document(file_name)

    # full_text_annotation -> Page -> Block -> Paragraph -> Word ->Symbols.
    print('type\tindex\tconfidence\tdata\ttemp1\ttemp2\n')
    for page in doc.pages:
        for block_index, block in enumerate(page.blocks):
            cv2.rectangle(out, (block.bounding_box.vertices[0].x, block.bounding_box.vertices[0].y),
                          (block.bounding_box.vertices[2].x, block.bounding_box.vertices[2].y), (0, 0, 255),
                          thickness=10)

            block_sentence = ""
            for paragraph in block.paragraphs:
                sentence = ""
                for word in paragraph.words:
                    word_text = ''.join([symbol.text for symbol in word.symbols])
                    sentence = sentence + word_text
                block_sentence = block_sentence + sentence

            print('Block\t{}\t{}\t{}\t{}\t{}'.format(block_index, block.confidence, block_sentence,
                                                     (block.bounding_box.vertices[0].x,
                                                      block.bounding_box.vertices[0].y),
                                                     (block.bounding_box.vertices[2].x,
                                                      block.bounding_box.vertices[2].y)))

            for para_index, paragraph in enumerate(block.paragraphs):
                cv2.rectangle(out, (paragraph.bounding_box.vertices[0].x, paragraph.bounding_box.vertices[0].y),
                              (paragraph.bounding_box.vertices[2].x, paragraph.bounding_box.vertices[2].y), (0, 255, 0),
                              thickness=5)

                sentence = ""
                for word in paragraph.words:
                    word_text = ''.join([symbol.text for symbol in word.symbols])
                    sentence = sentence + word_text
                print(
                    'Paragraph\t{}\t{}\t{}'.format(str(block_index) + "_" + str(para_index), paragraph.confidence,
                                                   sentence))

                for word in paragraph.words:
                    cv2.rectangle(out, (word.bounding_box.vertices[0].x, word.bounding_box.vertices[0].y),
                                  (word.bounding_box.vertices[2].x, word.bounding_box.vertices[2].y), (255, 0, 0),
                                  thickness=1)
                    word_text = ''.join([symbol.text for symbol in word.symbols])
                    print('Word\t{}\t{}\t{}'.format("", word.confidence, word_text))

                    # for symbol in word.symbols:
                    #     print('\tdebug: Symbol: {} (confidence: {})'.format(
                    #         symbol.text, symbol.confidence))

    output_img_name = output_image_dir + "/" + os.path.basename(file_name)
    cv2.imwrite(output_img_name, out)


if __name__ == '__main__':
    output_setting()
    image_list = glob.glob(input_image_dir + "/*.png")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "_credentials.json"
    client: ImageAnnotatorClient = vision.ImageAnnotatorClient()
    # https://googleapis.github.io/google-cloud-python/latest/vision/gapic/v1/api.html

    for file_name in image_list:
        analyze_document(file_name)
