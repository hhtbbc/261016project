/* V67 inference derived from the V60 worker. Background fixed at compile time.
 * The packet layout and convolution arithmetic stay identical to V60. */
#define main v57_main
#include "swarm_history_worker_v57.c"
#undef main
#define L 29
#define Y 36
#define X 72
#define CELL (L*Y*X)
static double raw[3][CELL], output[3][CELL];
static double state[3][Y*X], a[8][Y*X], b[8][Y*X];
static double parameters[1027], mean[L], deviation[L];

static int load(const char *path, double *dst, size_t n)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    int ok = fread(dst, sizeof(double), n, f) == n && fgetc(f) == EOF;
    fclose(f);
    return ok;
}

static void conv(const double *src, int in, double *dst, int out,
                 const double *weight, int relu)
{
    const double *bias = weight + out*in*9;
    for (int o=0; o<out; ++o)
        for (int y=0; y<Y; ++y)
            for (int x=0; x<X; ++x) {
                double value = bias[o];
                for (int i=0; i<in; ++i)
                    for (int dy=-1; dy<=1; ++dy)
                        for (int dx=-1; dx<=1; ++dx) {
                            int row = y+dy, col = (x+dx+X)%X;
                            if (row<0) row=-row;
                            if (row>=Y) row=2*Y-2-row;
                            value += src[(i*Y+row)*X+col] *
                                weight[((o*in+i)*3+dy+1)*3+dx+1];
                        }
                dst[(o*Y+y)*X+x] = relu && value<0 ? 0 : value;
            }
}

int main(int argc, char **argv)
{
    if ((argc!=2 && argc!=5) || chroot(argv[1]) || chdir("/") ||
        setgroups(0,NULL) || setgid(65534) || setuid(65534) ||
        prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0) || restrict_syscalls())
        return 2;
    if (argc==5) {
        if (probe(argv[2]))
            return 3;
        for (int i=3;i<5;++i) {
            int fd=open(argv[i],O_RDONLY);
            if (fd>=0) { close(fd); return 3; }
            printf("raw_or_archived_source_rejected_%d=%d\n",i,errno);
        }
        return 0;
    }
    static double packet[1027+2*L];
    if (!load("/anchors.txt",&raw[0][0],3*CELL) ||
        !load("/model.bin",packet,1027+2*L))
        return 4;
    memcpy(parameters,packet,sizeof(parameters));
    memcpy(mean,packet+1027,sizeof(mean));
    memcpy(deviation,packet+1027+L,sizeof(deviation));
    for (int l=0;l<L;++l) {
        for (int i=0;i<3;++i)
            for (int p=0;p<Y*X;++p) {
                double v=raw[i][l*Y*X+p];
                if (!isfinite(v)||v<=0||!isfinite(deviation[l])||deviation[l]<=0)
                    return 5;
                state[i][p]=(log(v)-mean[l])/deviation[l];
            }
        conv(&state[0][0],3,&a[0][0],8,parameters,1);
        conv(&a[0][0],8,&b[0][0],8,parameters+224,1);
        conv(&b[0][0],8,&state[0][0],3,parameters+808,0);
        for (int i=0;i<3;++i)
            for (int p=0;p<Y*X;++p) {
                int j=l*Y*X+p;
                #ifdef LT_BACKGROUND
                const int offsets[]={6,12,21};
                int source=j-j%X+(j%X+offsets[i])%X;
#else
                int source=j;
#endif
                double v=raw[2][source]*exp(state[i][p]);
                if (!isfinite(v)||v<=0)
                    return 6;
                output[i][j]=v;
            }
    }
    return fwrite(output,sizeof(output),1,stdout)==1 && fflush(stdout)==0 ? 0 : 7;
}
