import logging
import numpy as np


# Nullチェックし、値がなければExceptionで落とす
# 全valueデータをvalidateチェックすると重いので単純チェックのみにしている
def validator_and_return_val(vali, input_word: str, *pram) -> str:
    # 値が、空かどうかをチェックする
    # word が空以外にスペースのみ入っているケースもあるため、それもエラーとする
    if isinstance(input_word, str):
        check_word = input_word.replace(" ", "").replace("　", "")
        if not check_word:
            print("1: data check error:", input_word, pram)
            raise Exception
        # if not vali.validate({'str_common': check_word}):
        #     print("data check error:", input_word, pram)
        #     logging.error(vali.errors)
        #     raise Exception
    else:
        # intやfloat系の想定
        if np.isnan(input_word):
            print("2: data check error:", input_word, pram)
            raise Exception

    return input_word


# 空文字やNullでもなく、nanでもないことをチェックする
def validate(input_data) -> bool:
    return input_data and not (isinstance(input_data, float) and np.isnan(input_data))

