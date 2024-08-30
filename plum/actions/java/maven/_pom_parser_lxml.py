import logging
from lxml import etree as ET
from pathlib import Path
import re
from typing import List, Literal, Tuple, Union
from queue import Queue


class PomXML():
    """
    Modify and manage Maven `pom.xml` files.
    The `pom.xml` file is an XML Project Object Model file that
    contains the configuration for a Maven project.
    """
    def __init__(
        self,
        pom_path: Union[str, Path],
        namespace: str,
        tree: ET.ElementTree,
        indents: str = "   "
    ):
        """
        Args:
            namespace: Namespace of the XML elements.
            tree: XML tree object.
            indents: Indentation level used in the XML file. Defaults to 3 spaces.
        """
        self._pom_path = Path(pom_path)
        self.namespace = namespace
        self._tree = tree
        self._root = tree.getroot()
        self._indents = indents

    @staticmethod
    def from_file(pom_file: Union[Path, str]):
        """Parse pom.xml file from given path."""
        # Parse the XML file
        tree = ET.parse(pom_file)
        root = tree.getroot()

        # Extract namespace from the root element
        ns_match = re.match(r'\{.*\}', root.tag)
        ns = ns_match.group(0) if ns_match else ''
        if not ns:
            logging.error(
                "Unable to extract namespace from the root element. Continuing with no namespace."
            )

        # Determine indentation level
        indents = PomXML._determine_indentation(tree)

        return PomXML(
            pom_path=pom_file,
            namespace=ns,
            tree=tree,
            indents=indents
        )

    @staticmethod
    def _determine_indentation(xml_tree: ET.ElementTree):
        """Determine the number of spaces used for indentation in the XML file."""
        root = xml_tree.getroot()
        for elem in root.iter():
            if elem.text and '\n' in elem.text:
                # Find the first occurrence of newline and take the substring that follows
                indents = elem.text.split('\n')[-1]
                return indents
        logging.warning("Could not determine indentation level from the XML structure. Defaulting to 3 spaces.")
        return " " * 3  # Default indentation level if unable to determine

    def save_to_disk(self, output_file: Union[Path, str] = None):
        """
        Write the XML tree to a file.

        Args:
            output_file: Path to the output file. Defaults to the original pom.xml file.
        """
        if output_file is None:
            output_file = self._pom_path

        self._tree.write(
            output_file,
            pretty_print=True,
            xml_declaration=False,
            encoding='utf-8'
        )
        logging.info(f"pom.xml updated: {output_file}")

    def get_modules(self):
        """Retrieve the list of modules from the pom.xml file."""
        modules = []
        for module in self._root.findall(f'{self.namespace}modules/{self.namespace}module'):
            modules.append(module.text)
        return modules

    def find_all_submodules(self) -> Tuple[str, List[str]]:
        """
        Find all submodules in the current Maven repository.

        Modules declared in the pom.xml are subdirectories of the project that are also Maven projects themselves.
        These submodules can also declare their own modules, leading to a multi-level project structure.

        This method specifically traverses without using recursion to avoid deep recursion problems.

        Returns:
            A tuple containing the root directory of the Maven repository and a list of all
            submodules, relative to the root directory.
        """
        root_dir = self._pom_path.parent
        modules_queue = Queue()
        modules_queue.put(root_dir)
        all_directories = []

        while not modules_queue.empty():
            current_dir = modules_queue.get()

            if (current_dir / 'pom.xml').exists():
                relative_path = str(current_dir.relative_to(root_dir))
                all_directories.append(relative_path)

                pom = PomXML.from_file(current_dir / 'pom.xml')
                submodules = pom.get_modules()

                for submodule in submodules:
                    submodule_path = current_dir / submodule
                    if submodule_path.is_dir():
                        modules_queue.put(submodule_path)

        return str(root_dir), all_directories

    def add_maven_plugin(
        self,
        plugin_type: Literal["build", "reporting"],
        group_id: str,
        artifact_id: str,
        version: str
    ):
        """Add a given Maven plugin to the pom.xml file."""
        # Ensure the corresponding plugin type section exists. (<build> or <reporting>)
        # https://maven.apache.org/plugins/index.html
        level = 2
        plugin_type_section = self._root.find(f'{self.namespace}{plugin_type}')
        if plugin_type_section is None:
            plugin_type_section = ET.SubElement(self._root, f'{self.namespace}{plugin_type}')

            # Add correct indentation
            self._adjust_preceding_tail(plugin_type_section, level - 1)
            plugin_type_section.text = self._get_indent_for_level(level)
            plugin_type_section.tail = self._get_indent_for_level(level - 2)
            logging.info(f"<{plugin_type}> tag created")

        # Ensure <plugins> exists within <build> (or <reporting>)
        level += 1
        plugins = plugin_type_section.find(f'{self.namespace}plugins')
        if plugins is None:
            plugins = ET.SubElement(plugin_type_section, f'{self.namespace}plugins')

            # Add correct indentation
            plugins.text = self._get_indent_for_level(level)
            plugins.tail = self._get_indent_for_level(level - 2)
            logging.info("<plugins> tag created")

        # Check if specific plugin exists
        level += 1
        for plugin in plugins.findall(f'{self.namespace}plugin'):
            plugin_artifact_id = plugin.find(f'{self.namespace}artifactId')
            if plugin_artifact_id is not None and plugin_artifact_id.text == artifact_id:
                logging.info(f"{artifact_id} already exists, updating version")
                plugin_version = plugin.find(f'{self.namespace}version')
                plugin_version.text = version
                return

        # Plug in doesn't exist, add it. This is the plugin section.
        new_plugin = ET.SubElement(plugins, f'{self.namespace}plugin')
        new_plugin.text = self._get_indent_for_level(level)
        new_plugin.tail = self._get_indent_for_level(level - 2)

        # Add the plugin details
        gid = ET.SubElement(new_plugin, f'{self.namespace}groupId')
        gid.text = group_id
        aid = ET.SubElement(new_plugin, f'{self.namespace}artifactId')
        aid.text = artifact_id
        v = ET.SubElement(new_plugin, f'{self.namespace}version')
        v.text = version

        # Add correct indentation, these are all 1-liners on the same indentation level.
        # The only exception is version, which is the last detail, hence the tail needs to dedent.
        gid.tail = self._get_indent_for_level(level)
        aid.tail = self._get_indent_for_level(level)
        v.tail = self._get_indent_for_level(level - 1)
        logging.info(f"{artifact_id} added")

    def _get_indent_for_level(self, level):
        """Return the indentation for the given level."""
        return "\n" + self._indents * level

    def _adjust_preceding_tail(self, element, level):
        """Adjust the tail of the preceding element to match the given indentation level."""
        previous = element.getprevious()
        if previous is not None:
            previous.tail = self._get_indent_for_level(level)
        else:
            # If there is no preceding element, adjust the parent's text (if this is the first child)
            parent = element.getparent()
            if parent is not None and len(parent) > 0 and parent[0] == element:
                parent.text = self._get_indent_for_level(level)
