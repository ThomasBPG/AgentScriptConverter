# Quick Reference: GenAiPlannerBundle to Agent Script Migration

## Quick Start

```bash
# Run migration
python scripts/migrate_to_agent_script.py \
    force-app/main/default/genAiPlannerBundles/Agentforce_Employee_Agent/Agentforce_Employee_Agent.genAiPlannerBundle \
    force-app/main/default/agents/Agentforce_Employee_Agent.agent

# Review generated file
cat force-app/main/default/agents/Agentforce_Employee_Agent.agent

# Deploy to Salesforce
sf project deploy start --metadata Agent:Agentforce_Employee_Agent
```

## Key Concepts

### Hybrid Reasoning: `->` vs `|`

| Syntax | Purpose | Example |
|--------|---------|---------|
| `->` | Deterministic logic (always runs) | `run @actions.get_order with order_id = @variables.order_id` |
| `\|` | LLM prompt (suggestion) | `\| Help the customer with their order` |

### Action Execution Modes

```agentscript
# 1. Deterministic (always runs)
reasoning:
   instructions:->
      run @actions.get_order
         with order_id = @variables.order_id
         set @variables.status = @outputs.status

# 2. Tool (LLM chooses when to use)
reasoning:
   actions:
      lookup: @actions.get_order
         description: "Look up order details"
         with order_id = ...              # ... = LLM asks user
         set @variables.status = @outputs.status

# 3. Prompt mention (suggestion only)
reasoning:
   instructions:|
      Use {!@actions.get_order} when the customer provides an order number.
```

### Input Binding

```agentscript
with param = @variables.value        # Bind to variable
with param = "fixed_value"           # Fixed value
with param = ...                     # LLM asks user (slot-fill)
```

### Variables

```agentscript
variables:
   order_id: mutable string = ""              # Can change
   is_member: boolean = False                 # Immutable (no 'mutable')
   status: linked string                      # Set by action output only
   items: mutable list[string] = []           # Typed list
   metadata: mutable object = {}              # JSON object
```

**Important**: Use `True`/`False` (capitalized), not `true`/`false`.

## Common Migration Patterns

### Pattern 1: Converting Instructions to Deterministic Logic

**Before (Pure Prompt):**
```agentscript
reasoning:
   instructions:|
      Look up the order and tell the customer the status.
```

**After (Deterministic):**
```agentscript
reasoning:
   instructions:->
      if @variables.order_id is not None:
         run @actions.get_order
            with order_id = @variables.order_id
            set @variables.status = @outputs.status
         | The order status is {!@variables.status}. Share this with the customer.
      else:
         | Ask the customer for their order number.
```

### Pattern 2: Topic Transitions

```agentscript
# One-way transition (doesn't return)
start_agent topic_selector:
   reasoning:
      actions:
         go_help: @utils.transition to @topic.help_topic
            description: "Navigate to help"

# Or in deterministic logic
instructions:->
   if @variables.needs_help == True:
      transition to @topic.help_topic

# Delegation (returns after completion)
reasoning:
   actions:
      consult: @topic.specialist_topic
         description: "Consult specialist and return"
```

### Pattern 3: Conditional Tool Availability

```agentscript
reasoning:
   actions:
      cancel_order: @actions.cancel_order
         description: "Cancel the order"
         available when @variables.order_status == "processing"
         with order_id = @variables.order_id
```

### Pattern 4: Hiding Sensitive Data

```agentscript
actions:
   get_account:
      target: flow://Get_Account_Details
      outputs:
         account_name:
            type: string
            description: "Account name"
         credit_score:
            type: number
            description: "Internal credit score"
            filter_from_agent: True        # Hidden from LLM, but usable in logic
```

## Agent Script Cheat Sheet

| Operation | Syntax |
|-----------|--------|
| Reference variable | `@variables.name` |
| Interpolate in prompt | `{!@variables.name}` |
| Set variable | `set @variables.name = value` |
| Reference action | `@actions.name` |
| Reference topic | `@topic.name` |
| Run action | `run @actions.name with param = value` |
| Transition | `@utils.transition to @topic.name` |
| Escalate | `@utils.escalate` |
| If/else | `if condition: ... else: ...` |
| Comparison | `==`, `!=`, `>`, `<`, `>=`, `<=` |
| Logical | `and`, `or`, `not` |
| None check | `is None`, `is not None` |
| Arithmetic | `+`, `-` (in templates) |

## Common Pitfalls

### ❌ Don't Use lowercase booleans
```agentscript
# WRONG
if @variables.is_member == true:

# CORRECT
if @variables.is_member == True:
```

### ❌ Don't Use else if (not supported)
```agentscript
# WRONG
if condition1:
   ...
else if condition2:
   ...

# CORRECT (nested if/else)
if condition1:
   ...
else:
   if condition2:
      ...
```

### ❌ Don't Mix Tabs and Spaces
Pick one indentation method and stick with it (recommend 3 spaces per level).

### ❌ Don't Forget to Quote Strings with Special Characters
```agentscript
# WRONG
description: What's your question?

# CORRECT
description: "What's your question?"
```

## Post-Migration Checklist

- [ ] Review all action definitions (inputs/outputs correct?)
- [ ] Check variable types (string, number, boolean, object, list[type])
- [ ] Verify input bindings (slot-fill `...` vs explicit binding)
- [ ] Add deterministic logic where business rules must be enforced
- [ ] Test conditional branches (`if/else`)
- [ ] Validate topic transitions
- [ ] Check escalation configuration
- [ ] Test in Agentforce Builder
- [ ] Deploy and run end-to-end tests

## Useful Commands

```bash
# Check Python version
python3 --version

# Run migration with verbose output
python3 scripts/migrate_to_agent_script.py input.genAiPlannerBundle output.agent

# Validate (dry-run)
sf project deploy start --metadata Agent:AgentName --dry-run

# Deploy agent
sf project deploy start --metadata Agent:AgentName

# Deploy all agents
sf project deploy start --source-dir force-app/main/default/agents

# Retrieve agent from org
sf project retrieve start --metadata Agent:AgentName
```

## Resources

- **Full Migration Guide**: See `scripts/README_MIGRATION.md`
- **Agent Script Docs**: https://developer.salesforce.com/docs/ai/agentforce/guide/agent-script.html
- **Agent Script Reference**: https://github.com/aquivalabs/my-org-butler/blob/migration-to-agent-script/.claude/skills/agentforce/references/agent-script-guide.md
- **GenAiPlannerBundle Docs**: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_genaiplannerbundle.htm

---

**Quick Tip**: Start with the migrated `.agent` file as-is to ensure it works, then gradually refine by converting LLM prompts (`|`) to deterministic logic (`->`) for critical business rules.
