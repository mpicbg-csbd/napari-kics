
def segment(input_image, threshold=0.5):

    from skimage.color import rgb2gray

    if (len(input_image.shape)==3 and input_image.shape[-1]==3):
        img = rgb2gray(input_image)
    else:
        img = input_image


    print(img)
    return ((1-img)>threshold).astype(int)