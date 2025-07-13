#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Component mappings from reactstrap to react-bootstrap
const componentMappings = {
  // Card components
  'CardBody': 'Card.Body',
  'CardTitle': 'Card.Title',
  'CardSubtitle': 'Card.Subtitle',
  'CardText': 'Card.Text',
  'CardHeader': 'Card.Header',
  'CardFooter': 'Card.Footer',
  'CardImg': 'Card.Img',
  'CardGroup': 'CardGroup',
  
  // Form components
  'FormGroup': 'Form.Group',
  'FormText': 'Form.Text',
  'Input': 'Form.Control',
  'Label': 'Form.Label',
  'FormFeedback': 'Form.Control.Feedback',
  
  // Layout
  'Container': 'Container',
  'Row': 'Row',
  'Col': 'Col',
  
  // Navigation
  'NavItem': 'Nav.Item',
  'NavLink': 'Nav.Link',
  'NavbarBrand': 'Navbar.Brand',
  
  // Dropdown
  'UncontrolledDropdown': 'Dropdown',
  'DropdownToggle': 'Dropdown.Toggle',
  'DropdownMenu': 'Dropdown.Menu',
  'DropdownItem': 'Dropdown.Item',
  
  // Pagination
  'PaginationItem': 'Pagination.Item',
  'PaginationLink': 'Pagination.Item',
  
  // Others
  'UncontrolledAlert': 'Alert',
  'Badge': 'Badge',
  'Breadcrumb': 'Breadcrumb',
  'BreadcrumbItem': 'Breadcrumb.Item',
  'Spinner': 'Spinner',
  'Table': 'Table',
  'Alert': 'Alert',
  'Button': 'Button',
  'ButtonGroup': 'ButtonGroup',
  'Nav': 'Nav',
  'Navbar': 'Navbar',
  'Collapse': 'Navbar.Collapse',
  'Pagination': 'Pagination',
  'Card': 'Card',
  'ListGroup': 'ListGroup',
  'ListGroupItem': 'ListGroup.Item',
  'Form': 'Form',
};

// Read file content
function migrateFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Check if file imports from reactstrap
  if (!content.includes("from 'reactstrap'")) {
    return false;
  }
  
  console.log(`Migrating ${filePath}...`);
  
  // Extract imports from reactstrap
  const importRegex = /import\s*{([^}]+)}\s*from\s*['"]reactstrap['"]/g;
  const matches = content.match(importRegex);
  
  if (!matches) return false;
  
  matches.forEach(match => {
    // Extract component names
    const componentsMatch = match.match(/import\s*{([^}]+)}/);
    if (!componentsMatch) return;
    
    const components = componentsMatch[1]
      .split(',')
      .map(c => c.trim())
      .filter(c => c);
    
    // Group components by their react-bootstrap import
    const rbComponents = [];
    const needsMapping = new Map();
    
    components.forEach(comp => {
      if (componentMappings[comp]) {
        const rbComp = componentMappings[comp];
        if (rbComp.includes('.')) {
          // Components that need dot notation (e.g., Card.Body)
          const baseComp = rbComp.split('.')[0];
          if (!needsMapping.has(baseComp)) {
            needsMapping.set(baseComp, []);
          }
          needsMapping.get(baseComp).push({ original: comp, mapped: rbComp });
        } else {
          // Direct mapping components
          rbComponents.push(rbComp);
        }
      } else {
        // No mapping found, keep as is
        rbComponents.push(comp);
      }
    });
    
    // Build new import statement
    const importComponents = [...rbComponents];
    needsMapping.forEach((value, key) => {
      if (!importComponents.includes(key)) {
        importComponents.push(key);
      }
    });
    
    const newImport = `import { ${importComponents.join(', ')} } from 'react-bootstrap'`;
    content = content.replace(match, newImport);
    
    // Replace component usage in the file
    needsMapping.forEach((mappings) => {
      mappings.forEach(({ original, mapped }) => {
        // Replace opening tags
        const openTagRegex = new RegExp(`<${original}(\\s|>)`, 'g');
        content = content.replace(openTagRegex, `<${mapped}$1`);
        
        // Replace closing tags
        const closeTagRegex = new RegExp(`</${original}>`, 'g');
        content = content.replace(closeTagRegex, `</${mapped}>`);
        
        // Replace self-closing tags
        const selfCloseRegex = new RegExp(`<${original}(\\s[^>]*)/>`, 'g');
        content = content.replace(selfCloseRegex, `<${mapped}$1/>`);
      });
    });
  });
  
  // Fix specific prop changes
  content = content.replace(/\scolor="primary"/g, ' variant="primary"');
  content = content.replace(/\scolor="secondary"/g, ' variant="secondary"');
  content = content.replace(/\scolor="success"/g, ' variant="success"');
  content = content.replace(/\scolor="danger"/g, ' variant="danger"');
  content = content.replace(/\scolor="warning"/g, ' variant="warning"');
  content = content.replace(/\scolor="info"/g, ' variant="info"');
  content = content.replace(/\scolor="light"/g, ' variant="light"');
  content = content.replace(/\scolor="dark"/g, ' variant="dark"');
  
  // Fix tag prop for Card components
  content = content.replace(/\stag="h(\d)"/g, ' as="h$1"');
  
  // Fix Input to Form.Control
  content = content.replace(/<Input\s+type="select"/g, '<Form.Control as="select"');
  content = content.replace(/<Input\s+type="textarea"/g, '<Form.Control as="textarea"');
  content = content.replace(/<Input/g, '<Form.Control');
  content = content.replace(/<\/Input>/g, '</Form.Control>');
  
  // Write the migrated content back
  fs.writeFileSync(filePath, content);
  return true;
}

// Get all JS/JSX files
function getAllFiles(dirPath, arrayOfFiles) {
  const files = fs.readdirSync(dirPath);
  
  arrayOfFiles = arrayOfFiles || [];
  
  files.forEach(file => {
    const filePath = path.join(dirPath, file);
    if (fs.statSync(filePath).isDirectory()) {
      arrayOfFiles = getAllFiles(filePath, arrayOfFiles);
    } else if (file.endsWith('.js') || file.endsWith('.jsx')) {
      arrayOfFiles.push(filePath);
    }
  });
  
  return arrayOfFiles;
}

// Main execution
const srcPath = path.join(__dirname, 'src');
const files = getAllFiles(srcPath);

let migratedCount = 0;
files.forEach(file => {
  if (migrateFile(file)) {
    migratedCount++;
  }
});

console.log(`\nMigration complete! Migrated ${migratedCount} files.`);