# SXWIK

<div align="center">

### Linux Console

**A persistent Alpine Linux machine running inside QEMU through GitHub Actions.**

<a href="https://github.com/sxwik/sxwik/issues/1">
  <img src="./linux/screen.svg?v=linux-console" width="100%" alt="SXWIK Linux terminal">
</a>

**[Open the Linux console](https://github.com/sxwik/sxwik/issues/1)** · **[View workflow runs](https://github.com/sxwik/sxwik/actions)**

To use it, open the console issue and post a Linux shell command as a comment, for example:

```sh
uname -a
```

GitHub Actions boots the shared Alpine guest, runs your command, saves its filesystem state, and refreshes the terminal snapshot above. The profile image is a snapshot, not a live terminal.

</div>
