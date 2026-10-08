<div align="center">

# Tasfiya Tabassum

**Full-Stack Developer · Security Tooling · Experimental Interfaces**

Building useful experiments where systems, interfaces, and the modern web meet.

<img src="./assets/profile-cards/hero.svg?v=1" alt="Animated midnight glass hero" width="100%" />

</div>

## About

<img src="./assets/profile-cards/about-life.svg?v=1" alt="About and life cards" width="100%" />

I am a developer from **Khulna, Bangladesh**, working at **PulseByte Software**. My public work spans TypeScript, Python, real-time applications, browser APIs, WebAssembly, automation, responsible security research, and interactive interfaces.

## Stack

<img src="./assets/profile-cards/stack.svg?v=1" alt="Animated orbiting technology stack" width="100%" />

## Project atlas

| Project | Direction | Link |
|---|---|---|
| Stress-Tester | HTTP load generation, benchmarking and WAF auditing for authorized environments | [Explore](https://github.com/Quincunx33/Stress-Tester) |
| Bolt-share | Peer-to-peer file sharing and direct transfer workflows | [Explore](https://github.com/Quincunx33/Bolt-share) |
| Virtual-machine | Browser-based virtualization and emulation experiments | [Explore](https://github.com/Quincunx33/Virtual-machine) |
| EthicalHackingTools | Modular security testing and defensive analysis environment | [Explore](https://github.com/Quincunx33/EthicalHackingTools) |
| phishGard | Defensive phishing URL analysis | [Explore](https://github.com/Quincunx33/phishGard) |
| mycat-companion | Desktop companion, focus sessions and creative utility | [Explore](https://github.com/Quincunx33/mycat-companion) |

## Identity dashboard

<img src="./assets/profile-cards/id-dashboard.svg?v=1" alt="Animated ID badge and GitHub dashboard" width="100%" />

## GitHub 3D night-view workflow

The profile can be refreshed daily with [yoshi389111/github-profile-3d-contrib](https://github.com/yoshi389111/github-profile-3d-contrib). Add this workflow at `.github/workflows/profile-3d.yml`:

```yaml
name: Generate 3D contribution profile
on:
  schedule:
    - cron: "17 0 * * *"
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: yoshi389111/github-profile-3d-contrib@latest
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          USERNAME: Quincunx33
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: refresh 3D contribution profile"
```

## Connect

<img src="./assets/profile-cards/connect.svg?v=1" alt="Animated contact links" width="100%" />

- Portfolio: [taissu.pages.dev](https://taissu.pages.dev)
- Email: [liquiderror600@gmail.com](mailto:liquiderror600@gmail.com)
- GitHub: [@Quincunx33](https://github.com/Quincunx33)
- Instagram: [@tasfiya__tabassum__](https://www.instagram.com/tasfiya__tabassum__/)
- Facebook: [taissuuu](https://www.facebook.com/taissuuu)

> Security and penetration-testing projects are intended only for authorized labs, defensive analysis, responsible research, and learning.
