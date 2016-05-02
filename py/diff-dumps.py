import re, sys

def read(fname):
    ret = {}
    for line in open(fname,'r'):
        m = re.match(r"(\d+:\d+:\d+):(.*)", line.strip())
        if not m: continue
        (r,l,e) = map(int, m.group(1).split(":"))
        ret[(r,l,e)] = m.group(2)
    return ret

def diff(lists):
    allkeys = set()
    for ln,l in lists:
        for k in l.iterkeys(): allkeys.add(k)
    matched, mismatched, mia = [], [], []
    for k in allkeys:
        if any(l for l in lists if k not in l[1]):
            mia.append(k)
            continue
        ref = lists[0][1][k]
        if any(l for l in lists if l[1][k] != ref):
            mismatched.append(k)
        else:
            matched.append(k)
    print "matched   entries: %d" % len(matched)
    print "mimatched entries: %d" % len(mismatched)
    print "missing   entries: %d" % len(mia)

    maxlen = max(len(ln) for (ln,l) in lists)
    fmt = "%%6d:%%4d:%%12d   %%-%ds  %%s" % maxlen
    if mismatched:
        print ""                
        print " ---- MISMATCHED --- "
        for k in sorted(mismatched):
            for ln,l in lists:
                print fmt % (k[0],k[1],k[2],ln,l[k])
    if mia:
        print ""                
        print " ---- MISSING --- "
        for k in sorted(mia):
            for ln,l in lists:
                if k in l: print fmt % (k[0],k[1],k[2],ln,l[k])
                else:      print fmt % (k[0],k[1],k[2],ln,"<missing in action>")

if __name__ == '__main__':
    lists = [(fn,read(fn)) for fn in sys.argv[1:]]
    diff(lists)
