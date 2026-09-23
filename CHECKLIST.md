# Azure Migration Readiness Checklist

A practical, step-by-step checklist for moving servers and applications to Azure. Copy it
into your project tracker or a pull request and tick items as you go. Items marked
**[auto]** are covered (fully or partly) by `azmigrate-check`; run it early and re-run it
before every migration wave.

> This checklist is general guidance, not a substitute for the
> [Microsoft Cloud Adoption Framework](https://learn.microsoft.com/azure/cloud-adoption-framework/)
> or the [Azure Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/).
> Adapt it to your organisation's policies and regulatory requirements.

---

## 1. Discovery and assessment

- [ ] Define business goals, success criteria and constraints (deadline, budget, data residency)
- [ ] Nominate an executive sponsor, migration lead and an owner for every application
- [ ] Build a complete inventory of servers, databases, storage, network appliances and SaaS dependencies
- [ ] Record OS, version, vCPU, RAM, disk sizes, IPs, environment and owner per server **[auto]**
- [ ] Collect at least 2-4 weeks of performance data (CPU, memory, IOPS, throughput) for right-sizing **[auto: avg CPU]**
- [ ] Map application dependencies (ports, protocols, upstream/downstream systems, batch jobs)
- [ ] Classify each workload: rehost, replatform, refactor, replace (SaaS), retain or retire
- [ ] Identify licensing position (Windows Server, SQL Server, RHEL/SLES subscriptions, third-party software)
- [ ] Flag unsupported or end-of-support operating systems and databases **[auto]**
- [ ] Flag servers whose size or disk layout will not map cleanly to an Azure VM SKU **[auto]**
- [ ] Group workloads into migration waves (low-risk pilots first)
- [ ] Confirm target regions, and check VM SKU availability and subscription quotas in those regions

## 2. Identity and access

- [ ] Decide the tenant and subscription model (landing zone, management groups)
- [ ] Synchronise or federate on-prem identities with Microsoft Entra ID (Entra Connect / Cloud Sync)
- [ ] Decide how servers will authenticate: extend AD DS to Azure, Microsoft Entra Domain Services, or Entra ID login for VMs
- [ ] Define RBAC roles and assign them to groups, not individuals; apply least privilege
- [ ] Enable MFA and Conditional Access for all administrative accounts
- [ ] Set up Privileged Identity Management (PIM) for just-in-time elevation where licensed
- [ ] Replace embedded service credentials with managed identities where possible
- [ ] Create break-glass accounts and document their use

## 3. Networking

- [ ] Design the topology (hub-and-spoke or Virtual WAN) and IP address plan with no overlaps with on-prem
- [ ] Establish hybrid connectivity (Site-to-Site VPN or ExpressRoute) and test bandwidth and latency
- [ ] Plan DNS: private DNS zones, conditional forwarders, and name resolution in both directions
- [ ] Define Network Security Groups and/or Azure Firewall rules from the dependency map
- [ ] Remove direct public IPs from servers; use Azure Bastion for admin access **[auto: public IPs]**
- [ ] Publish internet-facing apps through Application Gateway (WAF) or Azure Front Door
- [ ] Use Private Endpoints for PaaS services (Storage, SQL, Key Vault)
- [ ] Plan for load balancers, static IPs and any hard-coded IP addresses in application config
- [ ] Confirm required outbound access (updates, licensing, monitoring) and route it via a controlled egress

## 4. Data and storage

- [ ] Choose the target for each database (Azure SQL Database, SQL Managed Instance, SQL on VM, Azure Database for PostgreSQL/MySQL)
- [ ] Run compatibility assessments for databases (e.g. Azure Migrate / Data Migration Assistant)
- [ ] Choose managed disk types (Standard HDD/SSD, Premium SSD, Premium SSD v2, Ultra) from IOPS/throughput data
- [ ] Check no single disk exceeds the managed disk size limit; plan striping if needed **[auto]**
- [ ] Choose the transfer method (online replication, Azure Data Box, AzCopy) based on data volume and window
- [ ] Plan file shares (Azure Files, Azure NetApp Files, Azure File Sync)
- [ ] Define data retention, archival tiers and lifecycle management
- [ ] Validate data residency and sovereignty requirements for each dataset
- [ ] Plan and rehearse data validation (row counts, checksums, application-level checks)

## 5. Security and compliance

- [ ] Enable Microsoft Defender for Cloud and review the secure score
- [ ] Store secrets, keys and certificates in Azure Key Vault; remove secrets from config files and scripts
- [ ] Enable encryption at rest (platform- or customer-managed keys) and in transit (TLS 1.2+)
- [ ] Patch and harden images before migration; plan ongoing update management
- [ ] Configure endpoint protection and vulnerability scanning on all VMs
- [ ] Send activity logs, resource logs and security events to a Log Analytics workspace / SIEM
- [ ] Map workloads to compliance requirements (e.g. ISO 27001, SOC 2, PCI DSS, HIPAA, GDPR) and assign Azure Policy initiatives
- [ ] Confirm that backups are configured for every production server **[auto]**
- [ ] Define and test disaster recovery (Azure Site Recovery, paired or secondary region), with documented RPO/RTO

## 6. Governance and cost management

- [ ] Define a tagging standard (e.g. owner, environment, cost-center, application) **[auto]**
- [ ] Enforce required tags and allowed regions/SKUs with Azure Policy
- [ ] Organise resources into management groups, subscriptions and resource groups by environment and ownership
- [ ] Apply resource locks to critical resources
- [ ] Set budgets and cost alerts per subscription or resource group
- [ ] Right-size VMs from performance data instead of copying on-prem sizes **[auto: oversized/underutilised]**
- [ ] Evaluate Azure Hybrid Benefit, Reservations and Savings Plans for steady-state workloads
- [ ] Schedule auto-shutdown for dev/test environments
- [ ] Produce a cost estimate with the Azure Pricing Calculator and review it with finance

## 7. Cutover

- [ ] Write a runbook per wave: steps, owners, timings, go/no-go criteria and rollback plan
- [ ] Run a test migration for every workload and complete user acceptance testing
- [ ] Take and verify a final backup of each source system
- [ ] Agree a change window and freeze; notify users and stakeholders
- [ ] Lower DNS TTLs ahead of the cutover
- [ ] Perform the final sync/replication and stop writes on the source
- [ ] Switch DNS, load balancers and integrations to Azure
- [ ] Run smoke tests and business validation; hold a go/no-go checkpoint
- [ ] Keep the source environment available (read-only or powered off) until the rollback window closes

## 8. Post-migration

- [ ] Monitor performance, availability and errors with Azure Monitor, alerts and dashboards
- [ ] Confirm Azure Backup jobs succeed and perform a test restore
- [ ] Right-size again after 2-4 weeks of production telemetry
- [ ] Review Azure Advisor recommendations (cost, security, reliability, performance)
- [ ] Update CMDB, architecture diagrams, runbooks and support contacts
- [ ] Decommission source servers, licences and data centre contracts, following data-disposal policy
- [ ] Hold a retrospective and feed lessons into the next wave
- [ ] Plan modernisation opportunities (PaaS, containers, managed databases)
