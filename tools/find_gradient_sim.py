import random, heapq
from math import hypot
random.seed(42)
N = 500
K = 200.0
G_HOP = 3.0
SOS = 180, 193
phones = []
for _ in range(N):
    while True:
        x, y = random.random()*K, random.random()*K
        if _ < 5:
            x, y = random.random()*40 + SOS[0]-30, random.random()*40 + SOS[1]-30
        phones.append((x, y))
        break
G = [[] for _ in phones]
for i in range(N):
    for j in range(i+1, N):
        if hypot(phones[i][0]-phones[j][0], phones[i][1]-phones[j][1]) < G_HOP:
            G[i].append(j); G[j].append(i)
def dijkstra(src):
    dist = [float('inf')]*len(phones); dist[src]=0
    pq=[(0,src)]
    while pq:
        d,u = heapq.heappop(pq)
        if d>dist[u]: continue
        for v in G[u]:
            if d+1<dist[v]: dist[v]=d+1; heapq.heappush(pq,(d+1,v))
    return dist
dist = dijkstra(SOS)
print("phones placed: %d  hop-radius=%.0fm  (crowd sits inside 200x200m)" % (N, G_HOP))
print("edges in radio-hearing graph: %d  avg degree %.1f" % (sum(len(x) for x in G)//2, sum(len(x) for x in G)/N))
print("gradient from SOS phone reaches %d/%d of the crowd in <=4 hops" % (sum(1 for d in dist if d<=4), N))
h = sum(1 for i in range(N) if dist[i]>0)
avg = sum(dist)/N if N else 0
print("avg hops to close the gradient across crowd: %.2f" % avg)
sos_dir = sum((phones[i][0]-SOS[0]) for i in range(N) if dist[i]<=2)/max(1,sum(1 for i in range(N) if dist[i]<=2))
sos_dy = sum((phones[i][1]-SOS[1]) for i in range(N) if dist[i]<=2)/max(1,sum(1 for i in range(N) if dist[i]<=2))
print("near-crowd mean displacement from SOS radio (should be ~0 = gradient pulls toward it): dx=%.2f dy=%.2f" % (sos_dir, sos_dy))
