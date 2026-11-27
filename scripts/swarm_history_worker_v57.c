#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

#define ALLOW(call) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, SYS_##call, 0, 1), \
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)

/* The static worker initializes libc before entering this deliberately small
 * x86-64 syscall policy. No sockets, native exec, namespace or process API. */
static int restrict_syscalls(void)
{
    struct sock_filter code[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        ALLOW(read), ALLOW(write), ALLOW(close), ALLOW(openat), ALLOW(newfstatat),
        ALLOW(fstat), ALLOW(lseek), ALLOW(getuid), ALLOW(getgid), ALLOW(geteuid),
        ALLOW(getegid), ALLOW(brk), ALLOW(mmap), ALLOW(munmap), ALLOW(exit_group),
        ALLOW(exit), ALLOW(rt_sigreturn),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)
    };
    struct sock_fprog program = {sizeof(code) / sizeof(code[0]), code};
    return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program);
}

static int probe(const char *outside)
{
    const char *paths[] = {outside, "../future.csv", "../../future.csv",
        "/escape", "/proc/self/fd/3", "/proc/1/root"};
    for (size_t i = 0; i < sizeof(paths) / sizeof(paths[0]); i++) {
        int fd = open(paths[i], O_RDONLY);
        if (fd >= 0) {
            close(fd);
            return 1;
        }
        printf("blocked_open_%zu=%d\n", i, errno);
    }
    if (open("/anchors.txt", O_WRONLY) >= 0 || errno != EACCES)
        return 1;
    puts("history_write=EACCES");
    if (socket(AF_INET, SOCK_STREAM, 0) >= 0 || errno != EPERM)
        return 1;
    puts("network_socket=EPERM");
    if (chroot("..") == 0 || errno != EPERM)
        return 1;
    puts("chroot_escape=EPERM");
    if (getuid() != 65534 || getgid() != 65534 || geteuid() != 65534 || getegid() != 65534)
        return 1;
    puts("unprivileged=65534");
    return 0;
}

int main(int argc, char **argv)
{
    if ((argc != 2 && argc != 3) || chroot(argv[1]) || chdir("/") ||
        setgroups(0, NULL) || setgid(65534) || setuid(65534) ||
        prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) || restrict_syscalls()) {
        perror("worker confinement");
        return 2;
    }
    if (argc == 3 && probe(argv[2]))
        return 3;
    FILE *input = fopen("/anchors.txt", "r");
    double first, last;
    char extra;
    if (!input || fscanf(input, "%lf %lf %c", &first, &last, &extra) != 2 ||
        !isfinite(first) || !isfinite(last) || first <= 0 || last <= 0)
        return 4;
    fclose(input);
    const int leads[] = {1, 3, 6};
    for (size_t i = 0; i < sizeof(leads) / sizeof(leads[0]); i++)
        printf("%d,%.17g,%.17g\n", leads[i], last, last + (leads[i] + 1) * (last - first));
    return ferror(stdout) != 0;
}
