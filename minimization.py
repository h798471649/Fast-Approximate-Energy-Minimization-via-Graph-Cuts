#!/usr/bin/env python


#usage of PyMaxflow which can do the graph cut efficiently using Kolmogorov's C++ implementation
import maxflow as mf
import numpy as np
import time

def image_to_array(img):
    '''input: path to image
       output: array of grayscale
       reference: https://stackoverflow.com/questions/40727793/how-to-convert-a-grayscale-image-into-a-list-of-pixel-values
       '''
    from PIL import Image
    img = Image.open(img).convert('L')
    w, h = img.size

    data = list(img.getdata())
    data = [data[off:off+w] for off in range(0, w*h, w)]

    return data

def arr_to_image(a, fname):
    '''Saves image arr as image'''
    from scipy.misc import toimage
    #pillow does not work properly. Don't know why
    # from PIL import Image
    # import matplotlib.pyplot as plt
    # arr = np.array(arr)
    # plt.imshow(arr)
    # plt.savefig('lol')
    # print(arr)
    # arr = np.random.random((100,100))
    
    # arr = np.asarray(dtype=np.dtype('uint8'), a=image_to_array("../test1noise.png"))
    # img = Image.fromarray(arr, 'L').convert('1')
    # img.show()
    # img.save("asdsadasd.jpeg")
    
    toimage(a).save(fname) 
    return 0

def give_test_1d_image():
    '''returns a 1x10 pixel image'''
    return np.array([[5, 4, 6, 5, 5, 4, 4, 3, 4, 3]])#,\
                     # [5, 5, 5, 5, 5, 2, 3, 2, 5, 5]])
    # return np.array([[5,5,3],[5,7,5]])

def graph_to_xdot(graph, map, revmap):
    '''prints out graph in xdot format
       graph: graph array
       map: mapping from adjacency-matrix-pos to (x,y)
       map: mapping from (x,y) to adjacency-matrix-pos'''
    #define graph
    out = "strict graph G{\nnode[color=white, style=filled];\n"
    #define terminal-nodes
    out += "\"alpha\"[color=red]\n "
    out += "\"beta\"[color=red]\n "
    #define all the other nodes(pixels)
    for (y,x) in revmap:
        out += "\"x="+ str(x) + ";y=" + str(y)+ "\"[color=red]\n "
    #add all edges
    for (y,x) in revmap:
        for j in range(1,len(graph)-1):
            if graph[revmap[(y,x)],j] != 0:
                y2, x2 = map[j]
                out +=  "\"x="+ str(x) + ";y=" + str(y) +"\"--" + "\"x="+ str(x2) + ";y=" + str(y2) + "\"[label=\""+str(graph[revmap[(y,x)]][j])+"\"]\n" 
    #add all edges from pixels to terminals 
    for i in range(1, len(graph)-1):
        y, x = map[i]
        out +=  "\"x="+ str(x) + ";y=" + str(y) +"\"--" + "\"alpha" + "\"[label=\""+str(graph[0][i])+"\"]\n"  
        out +=  "\"x="+ str(x) + ";y=" + str(y) +"\"--" + "\"beta" + "\"[label=\""+str(graph[-1][i])+"\"]\n"  

    out += "}"
    return out


def minimum_cut(graph, map, revmap):
    '''This functions calculates the minimum cut using the PyMaxflow library
       Input: graph, map and revmap
       output: list sorted in order of map with new label'''

    #first input is number of nodes, second is number of non-terminal edges
    graph_mf = mf.Graph[float](len(map),len(map))
    #add nodes
    nodes = graph_mf.add_nodes(len(map))

    #loop over adjacency matrix graph and add edges with weight
    for i in range(1, len(graph)-1):
        for j in range(i+1,len(graph)-1):
            if graph[i][j] > 0:
                graph_mf.add_edge(nodes[i-1],nodes[j-1], graph[i][j], graph[i][j])

    #add all the terminal edges
    for i in range(0,len(nodes)):
        graph_mf.add_tedge(nodes[i], graph[0][i+1], graph[-1][i+1])
   
    #computation intensive part; calculation of minimum cut
    flow = graph_mf.maxflow()
    return [graph_mf.get_segment(nodes[i]) for i in range(0, len(nodes))]
     
def V_p_q(label1, label2):
    '''Definition of the potential'''
    return abs(label1-label2)
    
    
def D_p(label, graph, i, j):
    '''Returns the quadratic difference between label and real intensity of pixel'''
    return (label-graph[i][j])**2


def give_neighbours(image, x, y):
    '''Returns a list of all neighbour intensities'''
    if x>=len(image[0]) or x<0 or y>=len(image) or y<0:
       raise ValueError('Pixel is not in image. x and/or y are to large')
    ns = []
    for a,b in zip([1,0,-1,0],[0,1,0,-1]):
        if (x+a<len(image[0]) and x+a>=0) and (y+b<len(image) and y+b>=0):
            ns.append(image[y+b][x+a])
    return ns 

def create_graph(img_orig, image,  alpha, beta):
    '''Method creates special graph using adjacency matrix as representation.
       image: is the array in greyscale
       alpha: alpha label
       beta: beta label
    '''
    #map does the position in the adjaceny matrix map to (y,x) position in image
    map = {}
    #other way 
    revmap = {}
    #loop over all pixels and add them to maps
    map_parameter = 1
    for i in range(len(image)):
        for j in range(len(image[0])):
            #extract pixel which have the wanted label
            if image[i][j] == alpha or image[i][j] == beta:
                map[map_parameter] = (i,j)
                revmap[(i,j)] = map_parameter
                map_parameter += 1


    n = len(map)
    #graph consists of all beta or alpha pixels
    #additionally 1 alpha and 1 beta node
    #alpha is at position 0, beta at n+1
    graph = np.zeros((n+2, n+2), dtype=np.float) 
    for i in range(1, n+1):
        #from alpha to all pixels
        y_img, x_img = map[i]
        #find neighbours
        neighbours = give_neighbours(image, x_img, y_img)
        #consider only neighbours which are not having alpha or beta label
        fil_neigh = list(filter(lambda i: i!=alpha and i!=beta, neighbours))
        #calculation of weight
        t_weight = sum([V_p_q(alpha,v) for v in fil_neigh])
        #setting graph weight for alpha terminal edges
        graph[i, 0] = D_p(alpha, img_orig, x_img, y_img)+t_weight
        graph[0, i] = graph[i, 0]
        #setting graph weight for beta terminal edges
        t_weight = sum([V_p_q(beta,v) for v in fil_neigh])
        graph[i, -1] = D_p(beta, img_orig, x_img, y_img)+t_weight
        graph[-1, i] = graph[i,-1]

    #neighbour have edges too
    for key in map:
        y,x = map[key]
        #search top, down, left, right neighbour
        for a,b in zip([1,0,-1,0],[0,1,0,-1]):
            if (y+a,x+b) in revmap:
                graph[key, revmap[(y+a,x+b)]] = V_p_q(alpha, beta) 
                graph[revmap[(y+a,x+b)], key] = V_p_q(alpha, beta)
        
    return graph, map, revmap

def alpha_beta_swap(alpha, beta, img_orig, img_work, time_measure=False):
    '''Performs alpha-beta-swap
       img_orig: input image 
       img_work: denoised image in each step
       time_measure: flag if you want measure time'''
    #create graph for this alpha, beta
    graph, map, revmap = create_graph(img_orig, img_work, alpha, beta)
    if time_measure == True:
        start = time.time() 
        res = minimum_cut(graph, map, revmap)
        end = time.time()
        # print(end-start)
    else:
        res = minimum_cut(graph, map, revmap)
    
    #depending on cut assign new label
    for i in range(0, len(res)):
        y,x = map[i+1] 
        if res[i] == 1:
            img_work[y][x] = alpha 
        else:
            img_work[y][x] = beta

    #time measurement
    if time_measure == True:
        return img_work, end-start
    else:
        return img_work

def main():
    import sys 
    from random import shuffle
    
    #image 
    img_name = sys.argv[1] 
    img_orig = image_to_array(img_name)
    img_work= image_to_array(img_name)
    

    #find all labels
    labels = []
    for i in range(0, len(img_orig)):
        for j in range(0, len(img_orig[0])):
            if img_orig[i][j] not in labels:
                labels.append(img_orig[i][j])
    
    print(labels) 
    T = 0
    #iterate over all pairs of labels 
    for u in range(0,2):
        # shuffle(labels)
        for i in range(0, len(labels)-1):
            for j in range(i+1, len(labels)):
                # print(i,j)
                img_work, dt = alpha_beta_swap(i,j, img_work, img_work, True)       
                T += dt 
        print("original image ", calculate_energy(img_orig, img_orig))
        print("denoised image ", calculate_energy(img_orig, img_work)) 

    arr_to_image(img_orig, "test_original.png")
    arr_to_image(img_work, "test_denoised.png")
    print(T)

    # print(calculate_energy(image_to_array(img_name), img_work)) 
    return 0 

def calculate_energy(img_orig, img_work):
    '''Calculates Energy of image.
       img: is input array'''

    E_data = 0
    for i in range(len(img_orig)):
        for j in range(len(img_orig[0])):
            E_data += D_p(img_orig[i][j], img_work, i, j)
    
    E_smooth = 0
    for i in range(len(img_orig)):
        for j in range(len(img_orig[0])):
            ns = give_neighbours(img_work, j, i)
            E_smooth += sum([V_p_q(v, img_work[i][j]) for v in ns])

    return E_data + E_smooth


def opencv_denoise():
    import numpy as np
    import cv2
    from matplotlib import pyplot as plt
    
    img = cv2.imread('../testimages/noisy_80.png')
    
    dst = cv2.fastNlMeansDenoisingColored(img,None,5,5,7,30)
    
    plt.subplot(121),plt.imshow(img)
    plt.subplot(122),plt.imshow(dst)
    plt.show()

main()
# opencv_denoise()