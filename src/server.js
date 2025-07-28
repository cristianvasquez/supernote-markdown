#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, "..");

class SupernoteMcpServer {
  constructor() {
    this.server = new Server(
      {
        name: "supernote-mcp-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "split_note",
            description: "Split a Supernote file into two separate files at a specified page",
            inputSchema: {
              type: "object",
              properties: {
                input_file: {
                  type: "string",
                  description: "Path to the input .note file to split"
                },
                split_page: {
                  type: "integer",
                  description: "Page number to split at (1-based). This page becomes the first page of the second file."
                },
                output_file1: {
                  type: "string",
                  description: "Path for the first part of the split note"
                },
                output_file2: {
                  type: "string",
                  description: "Path for the second part of the split note"
                },
                policy: {
                  type: "string",
                  enum: ["strict", "loose"],
                  description: "Parser policy for loading the note (default: strict)",
                  default: "strict"
                }
              },
              required: ["input_file", "split_page", "output_file1", "output_file2"]
            }
          },
          {
            name: "merge_notes",
            description: "Merge two Supernote files into a single file",
            inputSchema: {
              type: "object",
              properties: {
                input_file1: {
                  type: "string",
                  description: "Path to the first .note file to merge"
                },
                input_file2: {
                  type: "string",
                  description: "Path to the second .note file to merge"
                },
                output_file: {
                  type: "string",
                  description: "Path for the merged output file"
                },
                policy: {
                  type: "string",
                  enum: ["strict", "loose"],
                  description: "Parser policy for loading the notes (default: strict)",
                  default: "strict"
                }
              },
              required: ["input_file1", "input_file2", "output_file"]
            }
          },
          {
            name: "extract_images",
            description: "Extract all pages from a Supernote file as individual image files",
            inputSchema: {
              type: "object",
              properties: {
                input_file: {
                  type: "string",
                  description: "Path to the input .note file"
                },
                output_dir: {
                  type: "string",
                  description: "Directory to save the extracted image files"
                },
                format: {
                  type: "string",
                  enum: ["svg", "png"],
                  description: "Output image format (default: svg)",
                  default: "svg"
                },
                policy: {
                  type: "string",
                  enum: ["strict", "loose"],
                  description: "Parser policy for loading the note (default: strict)",
                  default: "strict"
                }
              },
              required: ["input_file", "output_dir"]
            }
          },
          {
            name: "extract_titles",
            description: "Extract all titles/anchors from a Supernote file as individual PNG images",
            inputSchema: {
              type: "object",
              properties: {
                input_file: {
                  type: "string",
                  description: "Path to the input .note file"
                },
                output_dir: {
                  type: "string",
                  description: "Directory to save the extracted title images"
                },
                invert: {
                  type: "boolean",
                  description: "Invert colors in the output images (default: false)",
                  default: false
                },
                policy: {
                  type: "string",
                  enum: ["strict", "loose"],
                  description: "Parser policy for loading the note (default: strict)",
                  default: "strict"
                }
              },
              required: ["input_file", "output_dir"]
            }
          },
          {
            name: "analyze_collection",
            description: "Analyze a collection of Supernote files and generate a summary report",
            inputSchema: {
              type: "object",
              properties: {
                directory: {
                  type: "string",
                  description: "Directory containing .note files to analyze"
                },
                output_file: {
                  type: "string",
                  description: "Output markdown file for the analysis report (default: supernote_collection_summary.md)",
                  default: "supernote_collection_summary.md"
                }
              },
              required: ["directory"]
            }
          }
        ]
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "split_note":
            return await this.handleSplitNote(args);
          case "merge_notes":
            return await this.handleMergeNotes(args);
          case "extract_images":
            return await this.handleExtractImages(args);
          case "extract_titles":
            return await this.handleExtractTitles(args);
          case "analyze_collection":
            return await this.handleAnalyzeCollection(args);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`
            );
        }
      } catch (error) {
        throw new McpError(
          ErrorCode.InternalError,
          `Tool execution failed: ${error.message}`
        );
      }
    });
  }

  async executeScript(scriptName, args) {
    const scriptPath = path.join(PROJECT_ROOT, `${scriptName}.py`);
    
    // Check if script exists
    try {
      await fs.access(scriptPath);
    } catch (error) {
      throw new Error(`Script not found: ${scriptPath}`);
    }

    return new Promise((resolve, reject) => {
      // Use uv to run Python scripts in the project environment
      const python = spawn("uv", ["run", "python", scriptPath, ...args], {
        cwd: PROJECT_ROOT,
        stdio: ["pipe", "pipe", "pipe"]
      });

      let stdout = "";
      let stderr = "";

      python.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      python.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      python.on("close", (code) => {
        if (code === 0) {
          resolve({ success: true, output: stdout, error: stderr });
        } else {
          reject(new Error(`Script failed with code ${code}: ${stderr}`));
        }
      });

      python.on("error", (error) => {
        reject(new Error(`Failed to execute script: ${error.message}`));
      });
    });
  }

  async handleSplitNote(args) {
    const { input_file, split_page, output_file1, output_file2, policy = "strict" } = args;
    
    const scriptArgs = [
      input_file,
      split_page.toString(),
      output_file1, 
      output_file2,
      "--policy", policy
    ];

    const result = await this.executeScript("split_note", scriptArgs);
    
    return {
      content: [
        {
          type: "text",
          text: `Successfully split note:\n${result.output}`
        }
      ]
    };
  }

  async handleMergeNotes(args) {
    const { input_file1, input_file2, output_file, policy = "strict" } = args;
    
    const scriptArgs = [
      input_file1,
      input_file2,
      output_file,
      "--policy", policy
    ];

    const result = await this.executeScript("merge_note", scriptArgs);
    
    return {
      content: [
        {
          type: "text",
          text: `Successfully merged notes:\n${result.output}`
        }
      ]
    };
  }

  async handleExtractImages(args) {
    const { input_file, output_dir, format = "svg", policy = "strict" } = args;
    
    const scriptArgs = [
      input_file,
      output_dir,
      "--format", format,
      "--policy", policy
    ];

    const result = await this.executeScript("extract_images", scriptArgs);
    
    return {
      content: [
        {
          type: "text",
          text: `Successfully extracted images:\n${result.output}`
        }
      ]
    };
  }

  async handleExtractTitles(args) {
    const { input_file, output_dir, invert = false, policy = "strict" } = args;
    
    const scriptArgs = [
      input_file,
      output_dir,
      "--policy", policy
    ];

    if (invert) {
      scriptArgs.push("--invert");
    }

    const result = await this.executeScript("extract_titles", scriptArgs);
    
    return {
      content: [
        {
          type: "text",
          text: `Successfully extracted titles:\n${result.output}`
        }
      ]
    };
  }

  async handleAnalyzeCollection(args) {
    const { directory, output_file = "supernote_collection_summary.md" } = args;
    
    const scriptArgs = [
      directory,
      "--output", output_file
    ];

    const result = await this.executeScript("analyze_collection", scriptArgs);
    
    return {
      content: [
        {
          type: "text",
          text: `Successfully analyzed collection:\n${result.output}`
        }
      ]
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Supernote MCP Server running on stdio");
  }
}

const server = new SupernoteMcpServer();
server.run().catch(console.error);