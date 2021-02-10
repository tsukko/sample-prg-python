import numpy as np
import cv2
from matplotlib.pyplot import figure, imshow
from skimage.color import rgb2lab
from skimage.exposure import rescale_intensity
from skimage.segmentation import slic
from sklearn.externals._pilutil import imresize
#from scipy.misc import imresize
from skimage import io, color, img_as_float

# SLIC(Simple Linear Iterative Clustering)、画像をsuperpixelに分割する
# https://qiita.com/mizukirc/items/2acec62b315b1d8e288d
# https://www.pyimagesearch.com/2017/06/26/labeling-superpixel-colorfulness-opencv-python/

image_file = "./Intermediate_img/isv01lpd_0.png"

def segment_colorfulness(image, mask):
	# split the image into its respective RGB components, then mask
	# each of the individual RGB channels so we can compute
	# statistics only for the masked region
	(B, G, R) = cv2.split(image.astype("float"))
	R = np.ma.masked_array(R, mask=mask)
	G = np.ma.masked_array(B, mask=mask)
	B = np.ma.masked_array(B, mask=mask)

	# compute rg = R - G
	rg = np.absolute(R - G)

	# compute yb = 0.5 * (R + G) - B
	yb = np.absolute(0.5 * (R + G) - B)

	# compute the mean and standard deviation of both `rg` and `yb`,
	# then combine them
	stdRoot = np.sqrt((rg.std() ** 2) + (yb.std() ** 2))
	meanRoot = np.sqrt((rg.mean() ** 2) + (yb.mean() ** 2))

	# derive the "colorfulness" metric and return it
	return stdRoot + (0.3 * meanRoot)


# step1 画像の読み込みと表示
orig = cv2.imread(image_file)
# orig_R = imresize(orig, 0.2)

# imshow(orig_R)
# cv2.imshow("step1", orig_R)
vis = np.zeros(orig.shape[:2], dtype="float")

# step2 スーパーピクセルを用いた画像の分割
# Ilab = rgb2lab(I)
# [Ls, N] = superpixels(Ilab, 1000, 'IsInputLab', true)
# Bmask = boundarymask(Ls)  # セグメンテーションの領域境界を検出
# I1 = imoverlay(I, Bmask,'c')   # スーパーピクセルを画像に重ね書き
# imshow(segments)

image = io.imread(image_file)
# image_R = imresize(image, 0.2)
segments = slic(img_as_float(image), n_segments=1000, slic_zero=True)

for v in np.unique(segments):
	# construct a mask for the segment so we can compute image
	# statistics for *only* the masked region
	mask = np.ones(image.shape[:2])
	mask[segments == v] = 0

	# compute the superpixel colorfulness, then update the
	# visualization array
	C = segment_colorfulness(orig, mask)
	vis[segments == v] = C

# scale the visualization image from an unrestricted floating point
# to unsigned 8-bit integer array so we can use it with OpenCV and
# display it to our screen
vis = rescale_intensity(vis, out_range=(0, 255)).astype("uint8")

# overlay the superpixel colorfulness visualization on the original
# image
alpha = 0.6
overlay = np.dstack([vis] * 3)
output = orig.copy()
cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)

cv2.imshow("Input", orig)
cv2.imshow("Visualization", vis)
cv2.imshow("Output", output)
cv2.waitKey(0)
#
# # スーパーピクセルごとの平均値を算出
# pixIdxList = label2idx(Ls)    # 各ラベル領域の行列インデックスを取得
# sz = numel(Ls)                # 画素数
# superLab = zeros(N, 3)
# for  i = 1:N
#   superLab(i,1) = mean(Ilab(pixIdxList{i}      ))  # L* mean
#   superLab(i,2) = mean(Ilab(pixIdxList{i}+   sz))  # a* mean
#   superLab(i,3) = mean(Ilab(pixIdxList{i}+ 2*sz))  # b* mean
# end
# I2 = label2rgb(Ls, lab2rgb(superLab))
#
# figure
# imshowpair(I, imoverlay(I2, boundarymask(Ls),'w'), 'montage')
#
#
# # K-meansで色の類似度を用いたクラスタリング
# numColors = 2
# [idx, cLab] = kmeans(superLab, numColors)
# Lc = zeros(size(Ls))
# for i = 1:N
#     Lc(pixIdxList{i}) = idx(i)
# end
#
# I3  = label2rgb(Lc, lab2rgb(cLab))
# I3b = imoverlay(I3, boundarymask(Lc), 'm')
#
# figure
# imshow(I3b)
#
# # 建物の部分のみを抽出
# maskA = (Lc == 1)
# maskA_filled = imfill(maskA, 'holes')       # マスクの穴を埋める
# Iout = imoverlay(I, maskA_filled, 'w')
#
# figure
# imshowpair(I, Iout)