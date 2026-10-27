#!/usr/bin/env python3
"""Regenerate php2shell-repo-dispatch.qflow.json from build-dispatches.js.

Run from the repo root: python3 qflow/build-qflow.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WF_ID = "6f2a1c3e-9b7d-4e21-8c55-2d1f0a9e7b41"
T, CS, JS, GH = "trigger", "node-5c1e2a90-integration-resource", "node-8d4b7f12-custom", "node-a73e6c05-http"
NO_RESOURCE = {"label": "NONE", "selectedResourceId": "NONE", "path": "", "context": {"outputPath": ""}}
NO_CONDITIONS = {"conditions": [], "expression": ""}
CS_FILTER = "state:RUNNING and (vulnerabilities.qid:389102 or vulnerabilities.qid:6877310)"


def from_node(node_id, label):
    return {"selectedResourceId": node_id, "path": "", "label": label, "context": {"outputPath": ""}}


def main():
    with open(os.path.join(HERE, "build-dispatches.js")) as f:
        code = f.read()

    components = [
        {"id": T, "name": "Trigger", "type": "trigger", "next": CS, "previous": None,
         "inputs": {
             "event": {"active": False, "value": {
                 "pattern": {}, "cloudProvider": "", "selectedServiceName": "", "selectedEventsName": "",
                 "selectedFilters": [{"values": [""], "key": ""}], "patternCheck": {}, "selectedEventsFiltersState": []}},
             "cloudview": {"active": False},
             "schedule": {"active": True, "value": [{"type": "rate", "value": "rate(15 minutes)"}]}},
         "target": {"script": "trigger"}, "selectedResource": None,
         "conditionalSettings": NO_CONDITIONS, "advanceOptions": {}},
        {"id": CS, "name": "CS: running containers with PHP2Shell", "type": "integration-resource", "next": JS, "previous": T,
         "inputs": {
             "integrationId": "", "provider": "cs", "connection": "", "api": "GET /containers",
             "params": {"filter": CS_FILTER, "pageSize": 50, "sort": "updated:desc"},
             "path": {}, "headers": {}, "pagination": {}},
         "target": {"script": "integration-resource"}, "selectedResource": NO_RESOURCE,
         "conditionalSettings": NO_CONDITIONS, "advanceOptions": {"disablePagination": False}},
        {"id": JS, "name": "Map image to source repo", "type": "custom", "next": GH, "previous": CS,
         "inputs": {"variables": {}, "code": code},
         "target": {"script": "customJavascript"},
         "selectedResource": from_node(CS, "CS: running containers with PHP2Shell"),
         "conditionalSettings": NO_CONDITIONS, "advanceOptions": {}},
        {"id": GH, "name": "GitHub repository_dispatch", "type": "http", "next": None, "previous": JS,
         "inputs": {
             "urlResolution": "external", "validateSsl": True, "methodName": "POST",
             "url": "https://api.github.com/repos/obj.repo/dispatches",
             "headers": [
                 {"key": "Accept", "value": "application/vnd.github+json"},
                 {"key": "X-GitHub-Api-Version", "value": "2022-11-28"},
                 {"key": "User-Agent", "value": "qualys-qflow-php2shell"}],
             "bodyType": "json",
             "body": {"event_type": "qualys-php2shell", "client_payload": {
                 "qid": "obj.qid", "image": "obj.image", "revision": "obj.revision",
                 "container_id": "obj.container_id", "host": "obj.host",
                 "detected_by": "Qualys Container Security via QFlow"}},
             # Paste the GitHub token in the editor after import; never commit it here.
             "auth": {"type": "bearer", "token": ""},
             "queryParams": {}, "suppressStatusCodes": [], "timeout": 30},
         "target": {"script": "http"},
         "selectedResource": from_node(JS, "Map image to source repo"),
         "conditionalSettings": NO_CONDITIONS, "advanceOptions": {}},
    ]
    categories = ["services", "accounts", "exclude_accounts", "regions", "resource_groups", "projects",
                  "solutions", "apps", "cloud_providers", "connectors", "oci_region", "compartment"]
    workflow = {
        "id": WF_ID, "workflow": WF_ID,
        "name": "PHP2Shell: running container to source repo (pipeline-demo)",
        "description": "Every 15 minutes, finds running containers with PHP2Shell (QID 389102 or 6877310) in "
                       "Container Security, maps each image to the GitHub repo that built it, and sends a "
                       "repository_dispatch so the repo's pipeline confirms with QScanner, bumps PHP and opens a PR.",
        "revision": None, "state": None, "active": True,
        "properties": {"priority": 1, "severity": 5, "categories": {k: [] for k in categories},
                       "editorVersion": "2.0", "hidden": False},
        "type": "normal",
        "definition": json.dumps({"variables": [], "components": components}),
    }
    with open(os.path.join(HERE, "php2shell-repo-dispatch.qflow.json"), "w") as f:
        json.dump(workflow, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
