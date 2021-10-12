from numpy import arctan,rad2deg,arcsin
import numpy as np
import psutil
import os
import pandas as pd

def uv2intdir(u, v):

    if u>0 and v>0:
        intensidade=np.sqrt((u*u)+(v*v))
        direcao=90-rad2deg(arctan(v/u))
    elif u<0 and v>0:
        intensidade=np.sqrt((u*u)+(v*v))
        direcao=rad2deg(arcsin(v/(-u)))+270
    elif u<0 and v<0:
        intensidade=np.sqrt((u*u)+(v*v))
        direcao=270-rad2deg(arctan((-v)/(-u)))
    elif u>0 and v<0:
        intensidade=np.sqrt((u*u)+(v*v))
        direcao=rad2deg(arctan((-v)/u))+90
    elif u==0 and v==0:
        intensidade=0
        direcao=0
    elif u==0 and v>0:
        intensidade=v
        direcao=0
    elif u==0 and v<0:
        intensidade=v
        direcao=180
    elif u>0 and v==0:
        intensidade=u
        direcao=90
    elif u<0 and v==0:
        intensidade=u
        direcao=270

    return intensidade,direcao

def deEmojify(inputString):
    return inputString.encode('ascii', 'ignore').decode('ascii')

def def_args_prefs(options, args, preferences):
    for arg in args:
        if type(arg) == list:
            options.add_argument(arg[0], arg[1])
        else:
            options.add_argument(arg)

    for preference in preferences:
        if type(preference) == list:
            options.set_preference(preference[0], preference[1])
        else:
            options.set_preference(preference[0])

    return options

def quit_driver(driver):
    driver_process = psutil.Process(driver.service.process.pid)
    #driver.quit()

    if driver_process.is_running():
        print ("driver is running")

        chrome_process = driver_process.children()
        if chrome_process:
            chrome_process = chrome_process[0]

            if chrome_process.is_running():
                print("chrome is still running, we can quit")
                driver.quit()
            else:
                print("chrome is dead, can't quit. Let's kill the driver")
                chrome_process.kill()
        else:
            print("driver has died")

    print("driver has died")

def mur_points():
    dict_mur = {'Ponto':
        [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61],
    'Lat':
        [-40.046,-39.1016,-38.0251,-37.0357,-36.0688,-35.0119,-34,-33.1005,-32.0212,-31.0093,-30.0198,-29.023,-28.0583,-27.0195,-26.0548,-25.0406,-24.0512,-23.7068,-23.3002,-23.2739,-22.9876,-22.0926,-21.0357,-20.0238,-20.0525,-19.8951,-19.0119,-18.045,-17.078,-16.0437,-15.0542,-14.0476,-13.0357,-12.0318,-10.9831,-9.9897,-9.1039,-8.0224,-7.0065,-6.0234,-5.1058,-5.4335,-4.7781,-4.5543,-3.5711,-2.9157,-2.2275,-2.2275,-2.2275,-1.6704,-0.3923,0.2959,0.6236,1.5084,2.5571,3.3764,3.9335,4.9738,5.7931,6.5796,6.9073],
    'Lon':
        [303.6982,304.1521,304.5141,305.3246,306.3242,307.4048,308.2928,309.4363,309.6464,309.8798,310.8133,311.4818,312.1492,312.3032,312.868,314.434,315.3839,316.0874,317.0645,318.0888,318.9779,319.9335,319.8168,320.2369,321.1662,322.0802,322.1973,322.6407,321.3805,322.0806,321.2405,321.1726,321.7093,322.6275,323.4097,324.4301,325.1784,325.5185,326,325.1444,325.125,325.0083,324.056,323.0696,322.0493,321.0289,320.0426,319.0902,318.0699,317.0155,316.0291,315.0768,314.0565,313.0701,312.0497,311.0634,310.043,308.9873,308.0424,307.0581,306.0738]
    }

    return pd.DataFrame(dict_mur)
