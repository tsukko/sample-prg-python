
# sample-prg-python

このリポジトリは、PDFファイルの解析・テキスト化・データ処理のためのサンプルプログラム集です。各フォルダごとに異なる機能や実験的コードがまとめられています。

## フォルダ構成と概要

### convert_pdf_to_text
PDFファイルをテキスト化するためのサンプルやユーティリティを収録。OCR（Tesseract、Google Cloud Vision）、画像変換、TensorFlowなど外部ツール連携のサンプルも含まれています。
作成日：2021年2月以前

### myframe
PDF解析やデータ処理のためのフレームワーク的なコード群。PDFMinerを使った共通処理（common_pdfminer.py）、パラメータ保存、テスト用PDFやK-meansクラスタリングのサンプルも含まれています。
作成日：2021年2月以前

### sample_pdfminer
PDFMinerを使ったPDF解析のサンプルや補助ツールを収録。テーブル抽出、画像変換、OCR、クラスタリング、ユーティリティなど、PDF処理の実験的コードが中心です。
作成日：2021年2月以前

### mp3_loudnorm
mp3ファイルの音量（ラウドネス）を解析・正規化するためのツール群。ffmpegを利用し、音量レポートのCSV出力やバッチ正規化処理が可能です。
作成日：2025年8月

mp3_loudnorm配下のPythonファイルを実行するために必要な主なツール・ライブラリは以下の通りです。
- Python標準ライブラリ
  - argparse, csv, json, re, subprocess, sys, time, logging, logging.handlers, pathlib, typing, dataclasses
- 外部ツール
  - ffmpeg（コマンドラインツール。音声解析・変換に必須）
追加のPythonパッケージインストールは不要ですが、ffmpegがシステムにインストールされている必要があります。

コマンド例：
`python convert_loudnorm_mp3.py -i /Users/XXX/Downloads/sample`

## 使い方
各フォルダ内のPythonスクリプトを直接実行して動作を確認できます。詳細は各ファイルのコメントやコードをご参照ください。

## ライセンス
本リポジトリのコードはMITライセンスです。

## 作者
tsukko
