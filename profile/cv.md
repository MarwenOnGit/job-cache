# Marouan Ben Hmed

**Offensive Security Engineer & Tooling Developer**

- Website: m0rgxn.me
- GitHub: MarwenOnGit
- HackTheBox: Top 5 nationally (Tunisia)
- Based in: Tunis, Tunisia

<!-- Contact details (email, phone) are deliberately left out of this committed copy.
     Put a full copy with contact details in cv/cv.md (gitignored); it overrides this file. -->

## Profile

Final-year computer engineering student in offensive security, working at the point where red
teaming meets software engineering. My focus is Azure and Entra ID, on-premises Active Directory,
and web application security, and most of what I do ends up as a tool or a lab other people can
run. I build offensive tooling, stand up hybrid attack ranges, and publish my research openly.
Ranked Top 5 nationally on HackTheBox with 70+ machines solved, and credited with a
triage-validated vulnerability in Grafana's disclosure program.

## Education

- **Engineering Degree in Computer Science**, National Engineering School of Tunis (ENIT), El Manar, Tunisia (Sept 2023 – present, final year)
- **Preparatory Studies for Engineering in Physics and Technology**, Preparatory Institute for Engineering Studies El Manar (Sept 2020 – Jul 2023). Ranked top 8% in the National Entrance Exam to Engineering Schools.

## Professional Experience

### Azure Red Team Intern — Keystone Group (Tunis, Tunisia) — Jul 2026 – Sep 2026
- Developed offensive tooling targeting Azure services by exploiting common cloud security misconfigurations.
- Extended open-source attack-path tooling in Python to model Azure and Entra ID assets and their abusable relationships, validating each modelled edge on a live tenant.
- Researched privilege-escalation paths involving Azure RBAC, managed identities, and service principals.

### White-Box Penetration Tester (Engagement) — Aug 2026
- Led a white-box security assessment of a production web application, working from source code to identify and validate high-impact vulnerabilities, including a remote code execution issue reported before the platform went live.
- Delivered a technical report with remediation guidance and proof-of-concept demonstrations for confirmed findings.

### Data Science Summer Intern — MAS Enterprise (Tunis, Tunisia) — Jun 2025 – Aug 2025
- Developed NLP models and data processing pipelines with a focus on reliability, reproducibility, and secure handling of enterprise data.
- Built monitoring dashboards to evaluate model performance and support deployment decisions.

### Technical Team Member — Securinets ENIT (Cybersecurity Club) — 2024 – present
- Helped run and maintain the CTF infrastructure for the club's competitions, and built web challenges that were well received by participants.

## Selected Projects

- **Fenrir — Azure Managed-Identity Attack-Path Tool** (github.com/MarwenOnGit/fenrir), Jul 2026 – present. Python CLI that automates the Azure managed-identity attack chain: tenant recon, IMDS token theft across VM, App Service, Logic App, Container and Automation hosts, and read-only tenant-wide post-exploitation enumeration. Models privilege-escalation primitives as data so a single rule set drives both a conservative go/no-go readiness verdict and the JSON output; multi-audience token minting (ARM / Storage / Key Vault) behind explicit CLI flags. Backed by a pytest suite of 146 passing tests.
- **Hybrid Active Directory & Entra ID Red Team Range**, Mar 2025 – present. Designed a large enterprise hybrid estate integrating on-premises Active Directory with Entra ID, with full red team infrastructure on AWS: Mythic C2, an Evilginx AiTM phishing instance and Cloudflare-fronted redirectors. Executed a full chain from cloud initial access to on-premises domain compromise (AiTM phishing, Pass-the-Cookie to Global Administrator, Azure Arc code execution to land a Mythic/Apollo implant), then constrained delegation, DCSync and a Golden Ticket for persistence. Presented the chain to an academic jury.
- **CVE Detection Lab** (github.com/MarwenOnGit/cve_detection_lab), 2026. Defensive research platform validating 10 high-severity 2026 CVEs against isolated vulnerable/patched Docker containers, with a multi-CVE verification script and detection signatures for Suricata/Snort, ModSecurity, Splunk/ELK and Sigma.
- **KESTREL — Autonomous RF Collection Swarm (design)**, 2026. Full system design for an autonomous multi-drone software-defined-radio swarm for lawful spectrum monitoring and emitter geolocation.
- **Network Analysis & Protocol Security Test Lab** (supervised project), 2024 – 2025. Isolated virtualised lab (Kali, Ubuntu, Windows) comparing insecure and secure protocols and reproducing ARP-spoofing and packet-injection scenarios with Bettercap, Scapy and Wireshark.

## Vulnerability Research & Publications

- **Grafana Labs (Intigriti VDP), 2026** — Reported a broken access control / improper authorization vulnerability (CVSS 6.5) in Grafana's Kubernetes-native Snapshot DELETE API; triage reproduced the proof of concept and forwarded it to Grafana.
- **Bug bounty / disclosure** — Active on Intigriti (Grafana Labs, Allegro sandbox); prepared a HackerOne submission documenting a hardcoded API key, CORS misconfiguration and an exposed internal service.
- **Technical writing (m0rgxn.me)** — Research write-ups on Azure managed-identity attacks (privilege escalation as an attack graph, the design of Fenrir, the credential-less identity model), plus in-depth HackTheBox attack-path and remediation write-ups.

## Competitions & Achievements

- **HackTheBox** — Ranked Top 5 nationally in Tunisia; 70+ machines solved across Windows and Linux at all difficulty levels; completed the Puppet Pro Lab.
- **HTB University CTF** — 77/1200 teams (2025); 308/1200 teams (2024).

## Skills

- **Cloud & Identity:** Azure, Entra ID, Azure RBAC, managed identities, service principals, AWS, on-premises Active Directory, ADCS
- **Red Team Operations:** Mythic C2, Sliver C2, Evilginx, redirectors, OPSEC-safe tooling, lateral movement, privilege escalation
- **Penetration Testing:** Enumeration, Active Directory, web application testing, whitebox source review
- **Tools:** BloodHound CE, AzureHound, Certipy, Impacket, Burp Suite, Nmap, Wireshark, Metasploit, Chisel, Proxychains, Neo4j, Exegol
- **Programming:** Python, Bash, C, C++, C#, .NET, Java, JavaScript
- **DevOps & Infra:** Docker, Terraform, Ansible, GitHub Actions, Git/GitHub
- **App Development:** React, Next.js, Node.js, Flask
- **Languages:** Arabic (native), French (fluent), English (fluent)

## Certifications

- HackTheBox CPTS (in progress, expected 2027)
- Certified Azure Red Team Professional (CARTP) (in preparation)
- Kubernetes for Red Teamers — SpecterOps Tradecraft Academy, 2026
- HackTheBox Pro Lab: Puppet (completed)
