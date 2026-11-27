/* Reuse the proven V57 chroot drop and syscall policy. */
#define main swarm_worker_v57_main
#include "swarm_history_worker_v57.c"
#undef main

#define CELLS (29 * 36 * 72)
static double history[3][CELLS];
static double output[3][CELLS];

int main(int argc, char **argv)
{
    if ((argc != 2 && argc != 3 && argc != 5) || chroot(argv[1]) || chdir("/") ||
        setgroups(0, NULL) || setgid(65534) || setuid(65534) ||
        prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) || restrict_syscalls()) {
        perror("V59 worker confinement");
        return 2;
    }
    if (argc > 2) {
        if (probe(argv[2]))
            return 3;
        if (argc == 5) {
            for (int i = 3; i <= 4; i++) {
                int fd = open(argv[i], O_RDONLY);
                if (fd >= 0) {
                    close(fd);
                    return 3;
                }
                printf("blocked_other_source_%d=%d\n", i, errno);
            }
        }
        return 0;
    }
    FILE *input = fopen("/anchors.txt", "rb");
    if (!input || fread(history, sizeof(history), 1, input) != 1 || fgetc(input) != EOF)
        return 4;
    fclose(input);
    const int leads[] = {1, 3, 6};
    for (size_t j = 0; j < sizeof(leads) / sizeof(leads[0]); j++) {
        const double n = leads[j] + 1;
        for (size_t i = 0; i < CELLS; i++) {
            double recent = history[2][i], previous = history[1][i];
            output[0][i] = isfinite(recent) && recent > 0 ? recent : NAN;
            output[1][i] = NAN;
            output[2][i] = NAN;
            if (isfinite(previous) && previous > 0 && isfinite(recent) && recent > 0) {
                output[1][i] = recent + n * (recent - previous);
                output[2][i] = exp(log(recent) + n * (log(recent) - log(previous)));
            }
        }
        if (fwrite(output, sizeof(output), 1, stdout) != 1)
            return 5;
    }
    return fflush(stdout) != 0;
}
