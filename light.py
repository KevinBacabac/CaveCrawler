from math import floor
LIGHT_RES = 9
def lightRegion(lightGrid, x, y, r, inty, color, brushesR):
    gX = floor((x + 0 - 0 % LIGHT_RES) / LIGHT_RES) + 1
    gY = floor((y + 0 - 0 % LIGHT_RES) / LIGHT_RES) + 1
    
    intensity = inty
    
    bOffx = gX - r
    bOffy = gY - r
    
    if intensity > 0.01:
        if (gX + r < len(lightGrid) or gX - r >= 0 or
            gY + r < len(lightGrid[0]) or gY - r >= 0):
            
            for i in range(gX - r, gX + r + 1):
                for j in range(gY - r, gY + r + 1):
                    if (i >= 0 and i < len(lightGrid) and
                        j >= 0 and j < len(lightGrid[0]) and
                        brushesR['Row'][i-bOffx][j-bOffy] <= r):
                        
                        brightnessIncrease = intensity * (r/(brushesR['Row'][i-bOffx][j-bOffy]) - 1)
                        
                        lightGrid[i][j][3] += brightnessIncrease
                        
                        if color is not None:
                            lightGrid[i][j][0] += brightnessIncrease * color.r
                            lightGrid[i][j][1] += brightnessIncrease * color.g
                            lightGrid[i][j][2] += brightnessIncrease * color.b
    
    return lightGrid