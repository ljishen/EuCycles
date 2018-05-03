# EuCycles

### Requirements

- `ansible >= 2.5` on control machine


### Usage

```bash
git clone https://github.com/ljishen/eucycles.git

# Enter the repo dir so that the ansible commands
# sees the ansible configuration file ansible.cfg
cd eucycles

# Install the role dependencies only once before the first run
ansible-galaxy install -r requirements.yml

# Run the playbook
# Replace DIR with the specific playbook you want to run
ansible-playbook -i playbooks/DIR/hosts playbooks/DIR/main.yml [--skip-tags install_docker]
```
