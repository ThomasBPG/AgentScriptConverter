# Migration from GenAI Planner Bundle to Agent Script

This directory contains scripts and documentation for migrating Salesforce GenAI Planner Bundles to the newer Agent Script format.

## Migration Script

The `migrate_to_agent_script.py` script converts a GenAI Planner Bundle into an Agent Script YAML file.

### Usage

```bash
python3 scripts/migrate_to_agent_script.py
```

This will generate a new Agent Script YAML file at:
`scripts/agent-scripts/Agentforce_Employee_Agent/agent.converted.yaml`

### Features

- Parses the GenAI Planner Bundle XML structure
- Extracts planner actions and local actions
- Reads input/output schema definitions from JSON files
- Maps properties to Agent Script skill format
- Generates comprehensive YAML with:
  - Agent metadata (name, description)
  - Goals and abilities
  - Skills with inputs/outputs
  - Knowledge sources and guardrails
  - Routing configuration

### Output Format

The generated YAML follows the Agent Script specification with:
- `name`: Agent name from bundle
- `description`: Agent description from bundle
- `goals`: Core objectives
- `abilities`: Functional capabilities
- `skills`: Individual action capabilities with inputs/outputs
- `knowledge`: Sources and topics
- `guardrails`: Data protection settings
- `routing`: Default and fallback routing

### Customization

To customize the output:
1. Modify the `build_agent_script` function in `migrate_to_agent_script.py`
2. Update mappings for invocation targets
3. Adjust goal/ability descriptions
4. Modify knowledge sources or guardrail settings

### Prerequisites

- Python 3.x
- PyYAML library (`pip3 install pyyaml`)
