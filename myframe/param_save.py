import glob
import os

# input_pdf_dir = "input"
output_dir = "output_pmn"
output_image_dir = output_dir + "/img"
intermediate_dir = "Intermediate_img"


class ParamSave:
    input_files = []
    save_file = ""

    def __init__(self, input_files):
        self.input_files = input_files

    def get_save_file(self):
        return self.save_file


class input_files_name:
    # 対象のファイル名から、さまざまな入出力用の名前を扱えるようにする
    # 例：
    # input file name :input_pdf_dir + "/sample_pdf.pdf"
    # base_name -> sample_pdf
    # output_file_name -> output_dir + "/res_sample_pdf.csv"
    # image_name -> intermediate_dir + "/sample_pdf_200_" + str(page_index) + ".png")
    def __init__(self, name):
        self.base_name = name

    def output_file_name(self, input_file_name):
        """
        保存ファイル名の生成
        :param input_file_name: 入力ファイル名
        :return: 保存ファイル名
        """
        name, ext = os.path.splitext(os.path.basename(input_file_name))
        return output_dir + "/res_" + name + ".csv"

    def get_image_name(self, page_index):
        # 変換した解像度の種類によって200、400などの数値が異なるが、ここでは気にしない。
        img_list = glob.glob(intermediate_dir + "/" + self.base_name + "_*_" + str(page_index) + ".png")
        return img_list[0]

    def get_save_image_path(self, img_file_name):
        return output_image_dir + "/" + os.path.basename(img_file_name)
