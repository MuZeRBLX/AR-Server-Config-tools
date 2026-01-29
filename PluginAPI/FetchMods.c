#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>
#include <libxml/HTMLparser.h>
#include <libxml/xpath.h>
#include <regex.h>
#include <ctype.h>
#include <math.h>

// Structure to hold HTTP response
typedef struct {
    char* data;
    size_t size;
} MemoryStruct;

static size_t WriteMemoryCallback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t realsize = size * nmemb;
    MemoryStruct* mem = (MemoryStruct*)userp;
    char* ptr = realloc(mem->data, mem->size + realsize + 1);
    if (!ptr) {
        fprintf(stderr, "[C ERROR] realloc() failed\n");
        return 0;
    }
    mem->data = ptr;
    memcpy(&(mem->data[mem->size]), contents, realsize);
    mem->size += realsize;
    mem->data[mem->size] = 0;
    return realsize;
}

// Helper: uppercase + trim whitespace
static char* str_upper_trim(const char* src) {
    if (!src || !*src) return NULL;
    size_t len = strlen(src);
    char* copy = malloc(len + 1);
    if (!copy) return NULL;
    size_t i = 0, j = 0;
    while (isspace((unsigned char)src[i])) i++;
    for (; src[i]; i++) {
        copy[j++] = toupper((unsigned char)src[i]);
    }
    while (j > 0 && isspace((unsigned char)copy[j-1])) j--;
    copy[j] = '\0';
    return copy;
}

// Returns size in GB (rounded to 3 decimals) or -1.0 on failure
double SizeConvert(const char* sizetext) {
    if (!sizetext || !*sizetext) return -1.0;
    char* text = str_upper_trim(sizetext);
    if (!text) return -1.0;
    double value = 0.0;
    char unit[16] = {0};
    int parsed = sscanf(text, "%lf %15s", &value, unit);
    free(text);
    if (parsed < 1) return -1.0;
    if (parsed == 1) return round(value * 1000.0) / 1000.0;
    if (strcmp(unit, "KB") == 0 || strcmp(unit, "KIB") == 0) value /= 1000000.0;
    else if (strcmp(unit, "MB") == 0 || strcmp(unit, "MIB") == 0) value /= 1000.0;
    else if (strcmp(unit, "GB") == 0 || strcmp(unit, "GIB") == 0) { /* already GB */ }
    else return -1.0;
    return round(value * 1000.0) / 1000.0;
}

// Helper: extract text from single XPath match
char* get_text_from_xpath(xmlDocPtr doc, const char* xpath_expr) {
    xmlXPathContextPtr context = xmlXPathNewContext(doc);
    xmlXPathObjectPtr result = xmlXPathEvalExpression((xmlChar*)xpath_expr, context);
    if (!result || xmlXPathNodeSetIsEmpty(result->nodesetval)) {
        xmlXPathFreeObject(result);
        xmlXPathFreeContext(context);
        return NULL;
    }
    xmlNodePtr node = result->nodesetval->nodeTab[0];
    xmlChar* text = xmlNodeGetContent(node);
    char* copy = text ? strdup((char*)text) : NULL;
    xmlFree(text);
    xmlXPathFreeObject(result);
    xmlXPathFreeContext(context);
    return copy;
}

// Helper: trim whitespace in-place
char* trim(char* str) {
    if (!str) return NULL;
    while (isspace((unsigned char)*str)) str++;
    if (*str == 0) return str;
    char* end = str + strlen(str) - 1;
    while (end > str && isspace((unsigned char)*end)) end--;
    end[1] = '\0';
    return str;
}

typedef struct {
    char* modId;
    char* name;
    char* version;
    char* size;
    char** deps;
    int dep_count;
} ModInfo;

void free_modinfo(ModInfo* info) {
    if (!info) return;
    free(info->modId);
    free(info->name);
    free(info->version);
    free(info->size);
    for (int i = 0; i < info->dep_count; i++) free(info->deps[i]);
    free(info->deps);
    free(info);
}

// Main function
ModInfo* fetch_mod_info(const char* item, char** seen_mods, int seen_count) {
    if (!item || !*item) {
        fprintf(stderr, "[C] Empty item\n");
        return NULL;
    }

    // Check if already seen
    for (int i = 0; i < seen_count; i++) {
        if (strcmp(seen_mods[i], item) == 0) {
            fprintf(stderr, "[C] Already seen: %s\n", item);
            return NULL;
        }
    }

    ModInfo* info = calloc(1, sizeof(ModInfo));
    if (!info) return NULL;
    info->modId = strdup(item);

    char url[256];
    snprintf(url, sizeof(url), "https://reforger.armaplatform.com/workshop/%s", item);

    CURL* curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "[C ERROR] curl_easy_init failed\n");
        free_modinfo(info);
        return NULL;
    }

    MemoryStruct chunk = { .data = malloc(1), .size = 0 };
    if (!chunk.data) {
        curl_easy_cleanup(curl);
        free_modinfo(info);
        return NULL;
    }

    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteMemoryCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void*)&chunk);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "Mozilla/5.0 (compatible; MARSCT/1.0)");
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);

    CURLcode res = curl_easy_perform(curl);
    long response_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);

    if (res != CURLE_OK || response_code != 200) {
        fprintf(stderr, "[C ERROR] Fetch failed: %s (HTTP %ld)\n", curl_easy_strerror(res), response_code);
        curl_easy_cleanup(curl);
        free(chunk.data);
        free_modinfo(info);
        return NULL;
    }

    curl_easy_cleanup(curl);

    // Parse HTML - very tolerant
    htmlDocPtr doc = htmlReadMemory(chunk.data, chunk.size, url, NULL,
                                    HTML_PARSE_RECOVER | HTML_PARSE_NOERROR | HTML_PARSE_NOWARNING);
    free(chunk.data);

    if (!doc) {
        fprintf(stderr, "[C ERROR] htmlReadMemory failed (size %zu bytes)\n", chunk.size);
        free_modinfo(info);
        return NULL;
    }

    fprintf(stderr, "[C] Successfully fetched and parsed HTML for %s (size %zu bytes)\n", item, chunk.size);

    // Extract name with fallbacks
    const char* name_xpaths[] = {
        "//h1[contains(@class,'text-3xl') and contains(@class,'font-bold')]",
        "//h1[contains(@class,'uppercase')]",
        "//h1"
    };
    info->name = NULL;
    for (int i = 0; i < 3 && !info->name; i++) {
        info->name = get_text_from_xpath(doc, name_xpaths[i]);
        if (info->name) {
            char* trimmed = trim(info->name);
            if (strlen(trimmed) == 0) {
                free(info->name);
                info->name = NULL;
            }
        }
    }
    if (!info->name) {
        fprintf(stderr, "[C] Name extraction failed - all XPaths\n");
        info->name = strdup("Name not found");
    } else {
        fprintf(stderr, "[C] Extracted name: '%s'\n", info->name);
    }

    // Extract version & size
    xmlXPathContextPtr ctx = xmlXPathNewContext(doc);
    xmlXPathObjectPtr divs = xmlXPathEvalExpression(
        (xmlChar*)"//div[contains(concat(' ', @class, ' '), ' flex ') and contains(concat(' ', @class, ' '), ' justify-between ') and contains(concat(' ', @class, ' '), ' border-b ')]",
        ctx);

    char* version = NULL;
    char* size_str = NULL;

    if (divs && divs->nodesetval) {
        fprintf(stderr, "[C] Found %d flex divs\n", divs->nodesetval->nodeNr);
        for (int i = 0; i < divs->nodesetval->nodeNr; i++) {
            xmlNodePtr div_node = divs->nodesetval->nodeTab[i];
            xmlNodePtr dt = NULL;
            xmlNodePtr dd = NULL;

            // Walk children to find dt and dd
            for (xmlNodePtr child = div_node->children; child; child = child->next) {
                if (child->type == XML_ELEMENT_NODE) {
                    if (!dt && xmlStrEqual(child->name, (xmlChar*)"dt")) {
                        dt = child;
                    } else if (dt && !dd && xmlStrEqual(child->name, (xmlChar*)"dd")) {
                        dd = child;
                    }
                }
            }

            if (dt && dd) {
                xmlChar* key_raw = xmlNodeGetContent(dt);
                xmlChar* val_raw = xmlNodeGetContent(dd);
                char* key_trim = key_raw ? trim((char*)key_raw) : NULL;
                char* val_trim = val_raw ? trim((char*)val_raw) : NULL;

                if (key_trim) {
                    fprintf(stderr, "[C] dt/dd pair: '%s' → '%s'\n", key_trim, val_trim ? val_trim : "NULL");
                    if (strstr(key_trim, "Version") &&
                    !strstr(key_trim, "size") &&
                    !strstr(key_trim, "Game")) {
                    free(version);
                    version = val_trim ? strdup(val_trim) : strdup("Version not found");
                } else if (strstr(key_trim, "size")) {
                        free(size_str);
                        size_str = val_trim ? strdup(val_trim) : NULL;
                    }
                }

                xmlFree(key_raw);
                xmlFree(val_raw);
            }
        }
    } else {
        fprintf(stderr, "[C] No flex divs found\n");
    }

    xmlXPathFreeObject(divs);
    xmlXPathFreeContext(ctx);

    info->version = version ? version : strdup("Version not found");

    // Size
    double size_gb = SizeConvert(size_str);
    free(size_str);
    if (size_gb >= 0.0) {
        char buf[64];
        snprintf(buf, sizeof(buf), "%.3f", size_gb);
        info->size = strdup(buf);
    } else {
        info->size = strdup("Size not found");
    }

    fprintf(stderr, "[C] Final extracted: version='%s', size='%s'\n", info->version, info->size);

    // Dependencies (your original code is fine)
    regex_t regex;
    if (regcomp(&regex, "/workshop/([A-F0-9]+)-", REG_EXTENDED) != 0) {
        xmlFreeDoc(doc);
        free_modinfo(info);
        return NULL;
    }

    xmlXPathContextPtr href_ctx = xmlXPathNewContext(doc);
    xmlXPathObjectPtr hrefs = xmlXPathEvalExpression((xmlChar*)"//a/@href", href_ctx);
    info->deps = NULL;
    info->dep_count = 0;

    if (hrefs && hrefs->nodesetval) {
        for (int i = 0; i < hrefs->nodesetval->nodeNr; i++) {
            xmlNodePtr node = hrefs->nodesetval->nodeTab[i];
            xmlChar* href = xmlNodeGetContent(node);
            regmatch_t matches[2];
            if (regexec(&regex, (char*)href, 2, matches, 0) == 0) {
                int start = matches[1].rm_so;
                int end = matches[1].rm_eo;
                char dep_id[64] = {0};
                int len = end - start;
                if (len > 0 && len < 64) {
                    strncpy(dep_id, (char*)href + start, len);
                    dep_id[len] = '\0';
                    info->deps = realloc(info->deps, (info->dep_count + 1) * sizeof(char*));
                    info->deps[info->dep_count++] = strdup(dep_id);
                }
            }
            xmlFree(href);
        }
    }

    xmlXPathFreeObject(hrefs);
    xmlXPathFreeContext(href_ctx);
    regfree(&regex);

    xmlFreeDoc(doc);

    fprintf(stderr, "[C] Dependencies found: %d\n", info->dep_count);

    return info;
}

#include <Python.h>

static PyObject* py_fetch_mod_info(PyObject* self, PyObject* args) {
    const char* item;
    PyObject* seen_list;

    if (!PyArg_ParseTuple(args, "sO", &item, &seen_list)) {
        return NULL;
    }

    Py_ssize_t seen_count = PyList_Size(seen_list);
    char** seen_mods = malloc(seen_count * sizeof(char*));
    if (!seen_mods) return PyErr_NoMemory();

    for (Py_ssize_t i = 0; i < seen_count; i++) {
        PyObject* str_obj = PyList_GetItem(seen_list, i);
        if (!PyUnicode_Check(str_obj)) {
            free(seen_mods);
            PyErr_SetString(PyExc_TypeError, "Seen mods must be strings");
            return NULL;
        }
        seen_mods[i] = PyUnicode_AsUTF8(str_obj);
    }

    ModInfo* info = fetch_mod_info(item, seen_mods, (int)seen_count);
    free(seen_mods);

    if (!info) {
        Py_RETURN_NONE;
    }

    PyObject* result = PyDict_New();
    PyDict_SetItemString(result, "modId", PyUnicode_FromString(info->modId));
    PyDict_SetItemString(result, "name", PyUnicode_FromString(info->name ? info->name : "Name not found"));
    PyDict_SetItemString(result, "version", PyUnicode_FromString(info->version ? info->version : "Version not found"));
    PyDict_SetItemString(result, "size", PyUnicode_FromString(info->size ? info->size : "Size not found"));

    PyObject* deps_list = PyList_New(info->dep_count);
    for (int i = 0; i < info->dep_count; i++) {
        PyList_SetItem(deps_list, i, PyUnicode_FromString(info->deps[i]));
    }
    PyDict_SetItemString(result, "deps", deps_list);

    free_modinfo(info);
    return result;
}

static PyMethodDef FetchModsMethods[] = {
    {"fetch_mod_info", py_fetch_mod_info, METH_VARARGS, "Fetch mod info from C"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef fetchmodsmodule = {
    PyModuleDef_HEAD_INIT,
    "fetchmods",   // must match "import fetchmods"
    NULL,
    -1,
    FetchModsMethods
};

PyMODINIT_FUNC PyInit_fetchmods(void) {
    return PyModule_Create(&fetchmodsmodule);
}