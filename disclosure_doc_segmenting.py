import os
import sys
import numpy as np
from keras.preprocessing.image import load_img, img_to_array, save_img
import PyPDF2

'''
To run this script: python disclosure_doc_segmenting.py <image file path> <directory path to save PDF output>
'''

args = sys.argv
IMAGEPATH = args[1] #filepath of image
OUTDIR = args[2]  #output directory


# load image as greyscale
img = load_img(IMAGEPATH, color_mode='grayscale')
# convert to numpy array
img_array = img_to_array(img)
nrow, ncol, ntup = img_array.shape
img_array_1d = img_array.reshape(nrow, ncol)

# Identify whitespaces - rows where all color values are white. The grayscale value for white is 255.
# The rows will be reduced to an array where 1 indicates a whitespace row and 0 otherwise.
img_array_rowiswhitespace = np.apply_along_axis(lambda x: 1 if (np.all(x==255)) else 0, 1, img_array_1d)

# Identify location and size of whitespaces by finding areas with consecutive whitespaces
# Dictionary - key = row index of the end/bottom of whitespace, value = number of consecutive rows in whitespace
whitespace_counter = 0
whitespace_sizes = {}
for (ws_pos, i) in enumerate(img_array_rowiswhitespace):
    if i == 1:
        whitespace_counter += 1
    else:
        if whitespace_counter != 0:
            whitespace_sizes[ws_pos] = whitespace_counter
            whitespace_counter = 0

# lower bound for outliers - whitespaces larger than 3rd quartile +1.5 IQR
q75, q25 = np.percentile(np.array(list(whitespace_sizes.values())), [75 ,25])
iqr = q75 - q25
outlier_lowerbd = q75+1.5*iqr

# Use the size of the whitespaces as a heuristic to determine where the image should be cut
# Use the outlier lower bound as an initial cutoff for whitespace size
init_cutpoints = {key: value for key, value in whitespace_sizes.items() if value > outlier_lowerbd}
cutpoints = init_cutpoints

# Iterate - reduce the number of cutpoints by dropping the cutpoint with the smallest sized whitespace,
# then split image at cutpoints and create PDFs
while len(cutpoints) > 0:
    n_seg = len(cutpoints)
    outpath = os.path.join(OUTDIR, 'n_seg_{}'.format(n_seg + 1))
    pdfs_to_merge = []
    if not os.path.exists(outpath):
        os.mkdir(outpath)
    for (i, pt) in enumerate(cutpoints.keys()):
        if i == 0:
            init_pt = 0
        else:
            init_pt = list(cutpoints.keys())[i-1]
        img_slice = img_array[init_pt:pt,]
        pagepath = os.path.join(outpath, 'doc_{0:02}.pdf'.format(i))
        # saves a single page PDF
        save_img(pagepath, img_slice)
        pdfs_to_merge.append(pagepath)
    #bottom segment of image
    img_slice = img_array[pt:, ]
    pagepath = os.path.join(outpath, 'doc_{0:02}.pdf'.format(n_seg + 1))
    save_img(pagepath, img_slice)
    pdfs_to_merge.append(pagepath)
    # saves a multi page PDF
    pdfWriter = PyPDF2.PdfFileWriter()
    # loop over PDFs
    for f in pdfs_to_merge:
        pdfFileObj = open(f,'rb')
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        for pageNum in range(pdfReader.numPages):
            pageObj = pdfReader.getPage(pageNum)
            pdfWriter.addPage(pageObj)
        os.remove(f)
    # save merged PDF
    pdfpath = os.path.join(outpath, 'n_seg_{}.pdf'.format(n_seg + 1))
    pdfOutput = open(pdfpath, 'wb')
    pdfWriter.write(pdfOutput)
    pdfOutput.close()
    print('PDF output ({} pages) {}'.format(n_seg + 1, pdfpath))
    cutpoints = {key: value for key, value in cutpoints.items() if value > min(cutpoints.values())}
