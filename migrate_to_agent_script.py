#!/usr/bin/env python3
"""
Migrate Salesforce GenAiPlannerBundle metadata to Agent Script format.

This script converts the XML-based GenAiPlannerBundle metadata structure
to the new YAML-like Agent Script (.agent) format used by Agentforce Builder.

Usage:
    python migrate_to_agent_script.py <input_bundle_path> [output_agent_path]

Example:
    python migrate_to_agent_script.py \
        force-app/main/default/genAiPlannerBundles/Agentforce_Employee_Agent/Agentforce_Employee_Agent.genAiPlannerBundle \
        force-app/main/default/agents/Agentforce_Employee_Agent.agent

References:
    - GenAiPlannerBundle: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_genaiplannerbundle.htm
    - Agent Script: https://developer.salesforce.com/docs/ai/agentforce/guide/agent-script.html / https://github.com/aquivalabs/my-org-butler/blob/migration-to-agent-script/.claude/skills/agentforce/references/agent-script-guide.md
"""

import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
import re


class GenAiPlannerBundleParser:
    """Parse GenAiPlannerBundle XML metadata."""

    def __init__(self, bundle_path: Path):
        self.bundle_path = bundle_path
        self.bundle_dir = bundle_path.parent
        self.namespace = "{http://soap.sforce.com/2006/04/metadata}"
        self.tree = ET.parse(bundle_path)
        self.root = self.tree.getroot()

    def _remove_namespace(self, tag: str) -> str:
        """Remove XML namespace from tag."""
        return tag.replace(self.namespace, "")

    def _get_text(self, element: ET.Element, tag: str, default: str = "") -> str:
        """Get text content of child element."""
        child = element.find(f"{self.namespace}{tag}")
        return child.text if child is not None and child.text else default

    def _get_bool(self, element: ET.Element, tag: str, default: bool = False) -> bool:
        """Get boolean value of child element."""
        text = self._get_text(element, tag, str(default).lower())
        return text.lower() == "true"

    def parse(self) -> Dict[str, Any]:
        """Parse the entire GenAiPlannerBundle."""
        return {
            "masterLabel": self._get_text(self.root, "masterLabel"),
            "description": self._get_text(self.root, "description"),
            "plannerType": self._get_text(self.root, "plannerType"),
            "plannerSurfaces": self._parse_planner_surfaces(),
            "plannerActions": self._parse_planner_actions(),
            "localTopics": self._parse_local_topics(),
            "localActionLinks": self._parse_action_links("localActionLinks"),
        }

    def _parse_planner_surfaces(self) -> List[Dict[str, Any]]:
        """Parse plannerSurfaces elements."""
        surfaces = []
        for surface in self.root.findall(f"{self.namespace}plannerSurfaces"):
            surfaces.append(
                {
                    "surface": self._get_text(surface, "surface"),
                    "surfaceType": self._get_text(surface, "surfaceType"),
                    "adaptiveResponseAllowed": self._get_bool(
                        surface, "adaptiveResponseAllowed"
                    ),
                    "callRecordingAllowed": self._get_bool(
                        surface, "callRecordingAllowed"
                    ),
                }
            )
        return surfaces

    def _parse_planner_actions(self) -> List[Dict[str, Any]]:
        """Parse plannerActions (global actions)."""
        actions = []
        for action in self.root.findall(f"{self.namespace}plannerActions"):
            action_data = self._parse_action_element(action)
            actions.append(action_data)
        return actions

    def _parse_local_topics(self) -> List[Dict[str, Any]]:
        """Parse localTopics (now becoming topic blocks)."""
        topics = []
        for topic in self.root.findall(f"{self.namespace}localTopics"):
            topic_data = {
                "fullName": self._get_text(topic, "fullName"),
                "developerName": self._get_text(topic, "developerName"),
                "localDeveloperName": self._get_text(topic, "localDeveloperName"),
                "masterLabel": self._get_text(topic, "masterLabel"),
                "description": self._get_text(topic, "description"),
                "scope": self._get_text(topic, "scope"),
                "language": self._get_text(topic, "language"),
                "pluginType": self._get_text(topic, "pluginType"),
                "canEscalate": self._get_bool(topic, "canEscalate"),
                "instructions": self._parse_plugin_instructions(topic),
                "utterances": self._parse_plugin_utterances(topic),
                "localActions": self._parse_topic_local_actions(topic),
                "localActionLinks": self._parse_topic_action_links(topic),
            }
            topics.append(topic_data)
        return topics

    def _parse_plugin_instructions(
        self, parent: ET.Element
    ) -> List[Dict[str, Any]]:
        """Parse genAiPluginInstructions elements."""
        instructions = []
        for instruction in parent.findall(
            f"{self.namespace}genAiPluginInstructions"
        ):
            instructions.append(
                {
                    "developerName": self._get_text(instruction, "developerName"),
                    "masterLabel": self._get_text(instruction, "masterLabel"),
                    "description": self._get_text(instruction, "description"),
                    "sortOrder": int(
                        self._get_text(instruction, "sortOrder", "0")
                    ),
                }
            )
        # Sort by sortOrder
        instructions.sort(key=lambda x: x["sortOrder"])
        return instructions

    def _parse_plugin_utterances(self, parent: ET.Element) -> List[Dict[str, Any]]:
        """Parse aiPluginUtterances elements."""
        utterances = []
        for utterance in parent.findall(f"{self.namespace}aiPluginUtterances"):
            utterances.append(
                {
                    "developerName": self._get_text(utterance, "developerName"),
                    "masterLabel": self._get_text(utterance, "masterLabel"),
                    "utterance": self._get_text(utterance, "utterance"),
                }
            )
        return utterances

    def _parse_topic_local_actions(self, topic: ET.Element) -> List[Dict[str, Any]]:
        """Parse localActions within a topic."""
        actions = []
        for action in topic.findall(f"{self.namespace}localActions"):
            action_data = self._parse_action_element(action)
            # Try to load schema files for this action
            action_data["schemas"] = self._load_action_schemas(
                topic, action_data["fullName"]
            )
            actions.append(action_data)
        return actions

    def _parse_action_element(self, action: ET.Element) -> Dict[str, Any]:
        """Parse a single action element (plannerAction or localAction)."""
        return {
            "fullName": self._get_text(action, "fullName"),
            "developerName": self._get_text(action, "developerName"),
            "localDeveloperName": self._get_text(action, "localDeveloperName"),
            "masterLabel": self._get_text(action, "masterLabel"),
            "description": self._get_text(action, "description"),
            "invocationTarget": self._get_text(action, "invocationTarget"),
            "invocationTargetType": self._get_text(action, "invocationTargetType"),
            "source": self._get_text(action, "source"),
            "isConfirmationRequired": self._get_bool(
                action, "isConfirmationRequired"
            ),
            "isIncludeInProgressIndicator": self._get_bool(
                action, "isIncludeInProgressIndicator"
            ),
            "progressIndicatorMessage": self._get_text(
                action, "progressIndicatorMessage"
            ),
        }

    def _parse_topic_action_links(self, topic: ET.Element) -> List[str]:
        """Parse localActionLinks within a topic."""
        links = []
        for link in topic.findall(f"{self.namespace}localActionLinks"):
            function_name = self._get_text(link, "functionName")
            if function_name:
                links.append(function_name)
        return links

    def _parse_action_links(self, tag_name: str) -> List[str]:
        """Parse action links (global or topic-level)."""
        links = []
        for link in self.root.findall(f"{self.namespace}{tag_name}"):
            function_name = self._get_text(link, "genAiFunctionName")
            if not function_name:
                function_name = self._get_text(link, "genAiPluginName")
            if function_name:
                links.append(function_name)
        return links

    def _load_action_schemas(
        self, topic: ET.Element, action_full_name: str
    ) -> Dict[str, Any]:
        """Load input/output schema JSON files for an action."""
        topic_full_name = self._get_text(topic, "fullName")

        # Build paths to schema files
        action_dir = (
            self.bundle_dir
            / "localActions"
            / topic_full_name
            / action_full_name
        )

        schemas = {"input": None, "output": None}

        for schema_type in ["input", "output"]:
            schema_path = action_dir / schema_type / "schema.json"
            if schema_path.exists():
                try:
                    with open(schema_path, "r") as f:
                        schemas[schema_type] = json.load(f)
                except Exception as e:
                    print(
                        f"Warning: Could not load {schema_path}: {e}",
                        file=sys.stderr,
                    )

        return schemas


class AgentScriptGenerator:
    """Generate Agent Script (.agent) from parsed GenAiPlannerBundle."""

    def __init__(self, parsed_data: Dict[str, Any]):
        self.data = parsed_data

    def _sanitize_name(self, name: str) -> str:
        """Convert name to valid Agent Script snake_case identifier."""
        # Remove IDs like _16jJ6000000oMwB or _179J6000000sawj
        name = re.sub(r"_[0-9A-Za-z]{15,18}$", "", name)
        # Convert to snake_case
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        # Remove invalid characters
        name = re.sub(r"[^a-z0-9_]", "_", name)
        # Remove consecutive underscores
        name = re.sub(r"__+", "_", name)
        # Remove trailing underscores
        name = name.rstrip("_")
        # Ensure starts with letter
        if name and not name[0].isalpha():
            name = "a_" + name
        # Max 80 chars
        return name[:80]

    def _map_lightning_type_to_agent_script(
        self, lightning_type: str, is_required: bool = False
    ) -> str:
        """Map Lightning type to Agent Script type."""
        type_map = {
            "lightning__textType": "string",
            "lightning__booleanType": "boolean",
            "lightning__numberType": "number",
            "lightning__objectType": "object",
            "lightning__dateType": "date",
            "lightning__richTextType": "string",
        }
        return type_map.get(lightning_type, "string")

    def _map_invocation_target(
        self, target: str, target_type: str, source: str
    ) -> str:
        """Map invocation target to Agent Script target format."""
        if target_type == "flow":
            return f"flow://{target}"
        elif target_type == "apex":
            return f"apex://{target}"
        elif target_type == "prompt":
            return f"prompt://{target}"
        elif target_type == "standardInvocableAction":
            # Standard actions - keep as is or map to known targets
            if source:
                # Use source as a hint for standard actions
                return f"flow://{source}"
            return f"flow://{target}"
        return f"flow://{target}"

    def _generate_action_definition(
        self, action: Dict[str, Any], indent: int = 6
    ) -> str:
        """Generate action definition block."""
        spaces = " " * indent
        action_name = self._sanitize_name(
            action.get("localDeveloperName") or action.get("developerName") or "unknown_action"
        )

        lines = [f"{spaces}{action_name}:"]
        lines.append(
            f'{spaces}   target: {self._map_invocation_target(action["invocationTarget"], action["invocationTargetType"], action.get("source", ""))}'
        )

        if action.get("description"):
            lines.append(f'{spaces}   description: "{action["description"]}"')

        if action.get("masterLabel"):
            lines.append(f'{spaces}   label: "{action["masterLabel"]}"')

        if action.get("isConfirmationRequired"):
            lines.append(f"{spaces}   require_user_confirmation: True")

        # Parse schemas if available
        schemas = action.get("schemas", {})

        if schemas.get("input"):
            input_schema = schemas["input"]
            properties = input_schema.get("properties", {})
            if properties:
                lines.append(f"{spaces}   inputs:")
                for prop_name, prop_def in properties.items():
                    prop_type = self._map_lightning_type_to_agent_script(
                        prop_def.get("lightning:type", "lightning__textType"),
                        prop_name in input_schema.get("required", []),
                    )
                    lines.append(f"{spaces}      {prop_name}: {prop_type}")

        if schemas.get("output"):
            output_schema = schemas["output"]
            properties = output_schema.get("properties", {})
            if properties:
                lines.append(f"{spaces}   outputs:")
                for prop_name, prop_def in properties.items():
                    prop_type = self._map_lightning_type_to_agent_script(
                        prop_def.get("lightning:type", "lightning__textType")
                    )
                    lines.append(f"{spaces}      {prop_name}:")
                    lines.append(f"{spaces}         type: {prop_type}")
                    if prop_def.get("description"):
                        lines.append(
                            f'{spaces}         description: "{prop_def["description"]}"'
                        )
                    # Check if this should be filtered from agent
                    if not prop_def.get("copilotAction:isUsedByPlanner", True):
                        lines.append(f"{spaces}         filter_from_agent: True")

        return "\n".join(lines)

    def _generate_topic_block(self, topic: Dict[str, Any]) -> str:
        """Generate a complete topic block."""
        topic_name = self._sanitize_name(
            topic.get("localDeveloperName") or topic.get("developerName") or "unknown_topic"
        )

        lines = [f"topic {topic_name}:"]

        if topic.get("description"):
            lines.append(f'   description: "{topic["description"]}"')

        # Add actions definitions
        if topic.get("localActions"):
            lines.append("")
            lines.append("   actions:")
            for action in topic["localActions"]:
                lines.append(self._generate_action_definition(action, indent=6))
                lines.append("")

        # Add reasoning block with instructions
        lines.append("   reasoning:")

        # Add instructions
        instructions = topic.get("instructions", [])
        if instructions:
            lines.append("      instructions:|")
            if topic.get("scope"):
                lines.append(f'         {topic["scope"]}')
                lines.append("")
            for instruction in instructions:
                lines.append(f'         {instruction["description"]}')
            lines.append("")

        # Add reasoning actions (tools the LLM can choose)
        if topic.get("localActions"):
            lines.append("      actions:")
            for action in topic["localActions"]:
                action_name = self._sanitize_name(
                    action.get("localDeveloperName") or action.get("developerName")
                )
                lines.append(f"         {action_name}_tool: @actions.{action_name}")
                if action.get("description"):
                    lines.append(
                        f'            description: "{action["description"]}"'
                    )

                # Add input bindings (use slot-fill for user inputs)
                schemas = action.get("schemas", {})
                if schemas.get("input"):
                    input_schema = schemas["input"]
                    properties = input_schema.get("properties", {})
                    for prop_name, prop_def in properties.items():
                        is_user_input = prop_def.get(
                            "copilotAction:isUserInput", False
                        )
                        if is_user_input:
                            lines.append(f"            with {prop_name} = ...")
                        # If not user input, we'd bind from variables or use fixed values
                        # This would need more context - for now, skip non-user inputs

                # Add output bindings
                if schemas.get("output"):
                    output_schema = schemas["output"]
                    properties = output_schema.get("properties", {})
                    for prop_name in properties.keys():
                        lines.append(
                            f"            set @variables.{prop_name} = @outputs.{prop_name}"
                        )

                lines.append("")

        # Add escalation if canEscalate is true
        if topic.get("canEscalate"):
            lines.append("         escalate_tool: @utils.escalate")
            lines.append('            description: "Transfer to a human agent"')
            lines.append("")

        return "\n".join(lines)

    def generate(self) -> str:
        """Generate complete Agent Script."""
        lines = []

        # Config block
        agent_name = self._sanitize_name(self.data.get("masterLabel", "Agent"))
        lines.append("config:")
        lines.append(f'   agent_name: "{agent_name}"')
        lines.append(f'   agent_label: "{self.data.get("masterLabel", "Agent")}"')
        if self.data.get("description"):
            lines.append(f'   description: "{self.data["description"]}"')
        lines.append("")

        # System block
        lines.append("system:")
        lines.append("   messages:")
        lines.append('      welcome: "Hello! How can I help you today?"')
        lines.append(
            '      error: "I\'m sorry, something went wrong. Please try again."'
        )
        if self.data.get("description"):
            lines.append(f'   instructions: "{self.data["description"]}"')
        lines.append("")

        # Connection block (if messaging surface exists)
        surfaces = self.data.get("plannerSurfaces", [])
        messaging_surface = next(
            (s for s in surfaces if s.get("surfaceType") == "Messaging"), None
        )
        if messaging_surface:
            lines.append("connection:")
            lines.append("   messaging:")
            lines.append("      outbound_route_type: queue")
            lines.append('      outbound_route_name: "Support_Queue"')
            lines.append(
                '      escalation_message: "Let me transfer you to a specialist."'
            )
            if messaging_surface.get("adaptiveResponseAllowed"):
                lines.append("      adaptive_response_allowed: True")
            lines.append("")

        # Variables block (extracted from action outputs)
        lines.append("variables:")
        lines.append("   # Variables will be populated from action outputs")
        lines.append("   # Add custom variables as needed")

        # Collect all unique output variables from all actions
        all_outputs = set()
        for topic in self.data.get("localTopics", []):
            for action in topic.get("localActions", []):
                schemas = action.get("schemas", {})
                if schemas.get("output"):
                    output_schema = schemas["output"]
                    properties = output_schema.get("properties", {})
                    for prop_name, prop_def in properties.items():
                        prop_type = self._map_lightning_type_to_agent_script(
                            prop_def.get("lightning:type", "lightning__textType")
                        )
                        # Only add if this is marked as used by planner
                        if prop_def.get("copilotAction:isUsedByPlanner", True):
                            all_outputs.add((prop_name, prop_type))

        for output_name, output_type in sorted(all_outputs):
            lines.append(f"   {output_name}: linked {output_type}")

        lines.append("")

        # Start agent block (topic router)
        lines.append("start_agent topic_selector:")
        lines.append('   description: "Routes user to the appropriate topic"')
        lines.append("   reasoning:")
        lines.append("      instructions:|")
        lines.append("         Analyze the user's message and select the best topic.")
        lines.append("")
        lines.append("      actions:")

        # Add transitions to each topic
        for topic in self.data.get("localTopics", []):
            topic_name = self._sanitize_name(
                topic.get("localDeveloperName") or topic.get("developerName")
            )
            lines.append(
                f"         go_to_{topic_name}: @utils.transition to @topic.{topic_name}"
            )
            if topic.get("description"):
                lines.append(f'            description: "{topic["description"]}"')

        # Add global actions as tools
        for action in self.data.get("plannerActions", []):
            action_name = self._sanitize_name(
                action.get("localDeveloperName") or action.get("developerName")
            )
            lines.append(f"         {action_name}_tool: @actions.{action_name}")
            if action.get("description"):
                lines.append(f'            description: "{action["description"]}"')

        lines.append("")

        # Global actions definitions (plannerActions)
        if self.data.get("plannerActions"):
            lines.append("# Global actions available across all topics")
            lines.append("actions:")
            for action in self.data["plannerActions"]:
                lines.append(self._generate_action_definition(action, indent=3))
                lines.append("")

        # Topic blocks
        for topic in self.data.get("localTopics", []):
            lines.append("")
            lines.append(self._generate_topic_block(topic))

        return "\n".join(lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(
            "Usage: python migrate_to_agent_script.py <input_bundle_path> [output_agent_path]"
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        # Default: same directory, replace extension with .agent
        output_path = input_path.parent / f"{input_path.stem}.agent"

    print(f"Parsing GenAiPlannerBundle: {input_path}")
    parser = GenAiPlannerBundleParser(input_path)
    parsed_data = parser.parse()

    print(f"Generating Agent Script...")
    generator = AgentScriptGenerator(parsed_data)
    agent_script = generator.generate()

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    with open(output_path, "w") as f:
        f.write(agent_script)

    print(f"✓ Agent Script generated: {output_path}")
    print(
        f"\nNext steps:"
        f"\n1. Review the generated .agent file"
        f"\n2. Adjust variable definitions and types as needed"
        f"\n3. Refine reasoning instructions to use -> for deterministic logic"
        f"\n4. Test the agent in Agentforce Builder"
        f"\n5. Deploy using Salesforce CLI: sf project deploy start --metadata Agent:{output_path.stem}"
    )


if __name__ == "__main__":
    main()
