src = open('demo/design/mycounter-false.aig','rb').read()
src = str(src)
print(src[2:-1])
src = src[2:-1]
print(src)
f = open('demo/design/mycounter-false-out.aig','w')
f.write(src)
for x in src:
    print(x)


