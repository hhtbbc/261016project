// Reuse the V57 Linux syscall policy. CNN runs as the unchanged V60 binary.
#define main v57_main
#include "swarm_history_worker_v57.c"
#undef main

#define X 72
#define CELL (29*36*X)
static double raw[3][CELL], daily[3][CELL], output[3][CELL];

static int load(const char *path, double *dst, size_t count)
{
    FILE *file=fopen(path,"rb");
    if (!file)
        return 0;
    int ok=fread(dst,sizeof(double),count,file)==count && fgetc(file)==EOF;
    fclose(file);
    return ok;
}

int main(int argc, char **argv)
{
    if ((argc!=2 && argc!=5) || chroot(argv[1]) || chdir("/") || setgroups(0,NULL) ||
        setgid(65534) || setuid(65534) || prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0) ||
        restrict_syscalls())
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
    if (!load("/anchors.txt",&raw[0][0],3*CELL) ||
        !load("/daily.bin",&daily[0][0],3*CELL))
        return 4;
    const int leads[]={1,3,6};
    for (int m=0;m<7;++m) {
        for (int h=0;h<3;++h)
            for (int j=0;j<CELL;++j) {
                int elapsed=leads[h]+1;
                double a0=log(raw[0][j]), a1=log(raw[1][j]), a2=log(raw[2][j]);
                double slope=(a2-a0)/2;
                double value;
                switch (m) {
                case 0: value=raw[2][j]; break;
                case 1: value=raw[2][j]+elapsed*(raw[2][j]-raw[1][j]); break;
                case 2: value=exp(a2+elapsed*(a2-a1)); break;
                case 3: value=exp((a0+a1+a2)/3+(leads[h]+2)*slope); break;
                case 4: value=exp(a2-3*expm1(-elapsed/3.0)*slope); break;
                case 5: value=raw[2][j-j%X+(j%X+3*elapsed)%X]; break;
                default: value=daily[h][j]; break;
                }
                output[h][j]=value;
            }
        if (fwrite(output,sizeof(output),1,stdout)!=1)
            return 7;
    }
    return fflush(stdout)==0 ? 0 : 7;
}
