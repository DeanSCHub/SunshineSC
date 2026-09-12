/**
 * JDE Work Order Paste & Master-Data Match
 * ------------------------------------------------------------------
 * Lets a technician paste a tab-separated block of work orders copied
 * from JDE, matches each row's Serial Number against the
 * crcc8_sunshineassetsapp master asset table in Dataverse, shows a
 * review grid (JDE fields + matched asset fields, unmatched rows
 * flagged), and on confirm creates the Work Order record(s) via the
 * Dataverse Web API directly (bypassing the native {% entityform %},
 * which cannot run this prefill/lookup logic).
 *
 * >>> CONFIG YOU MUST CONFIRM BEFORE GOING LIVE <<<
 * Everything below under CONFIG was inferred either directly from the
 * Master_Data_v2.xlsx "Dataversedata" export (high confidence) or is a
 * placeholder guess for the Work Order table (LOW confidence - this
 * table was not in any data we had access to). Open the Power Apps
 * maker portal > Tables, open each table's Columns list, and check the
 * "Schema Name" column against the values below.
 */
(function () {
  "use strict";

  // =========================================================================
  // CONFIG
  // =========================================================================

  // Master asset data table. Inferred from Master_Data_v2.xlsx "Dataversedata"
  // sheet: primary key column crcc8_sunshineassetsappid => table logical name
  // crcc8_sunshineassetsapp. Entity set name (plural, used in Web API URLs)
  // is a guess - verify by visiting {site}/_api/crcc8_sunshineassetsapps?$top=1
  // while signed in; if that 404s, check Table > Properties > "Entity Set
  // Name" in the maker portal and fix it here.
  var ASSET_TABLE = {
    entitySet: "crcc8_sunshineassetsapps",
    // Holds values in the same format as JDE's "Serial Number" column
    // (e.g. ADR-020306-ADRZB-INT) - confirmed against sample data rows.
    matchField: "crcc8_assetnumber",
    // Shown as their own columns in the main review table (KP first, per spec).
    primaryFields: [
      { name: "crcc8_kilometerpost", label: "KP", type: "number" },
      { name: "crcc8_location", label: "Location" },
      { name: "crcc8_assetclass", label: "Asset Class" },
      { name: "crcc8_assettype", label: "Asset Type" }
    ],
    // Everything else from the master table, tucked behind a "more details"
    // expander per row so the main grid stays readable. Add/remove freely -
    // this enumerates every non-system column found in the Dataversedata
    // export.
    secondaryFields: [
      { name: "crcc8_corridor", label: "Corridor" },
      { name: "crcc8_workgroup", label: "Work Group" },
      { name: "crcc8_crossboundary", label: "Cross Boundary", type: "boolean" },
      { name: "crcc8_trackstatus", label: "On/Off Track", type: "choice" },
      { name: "crcc8_shifttime", label: "Night/Day", type: "choice" },
      { name: "crcc8_accessdetails", label: "Access Via" },
      { name: "crcc8_fedfrom", label: "Fed From" },
      { name: "crcc8_resetfrom", label: "Reset From" },
      { name: "crcc8_drawingreference", label: "Drawing" },
      { name: "crcc8_bondingreference", label: "Bonding" },
      { name: "crcc8_saplocation", label: "SAP" },
      { name: "crcc8_inbiosite", label: "In a Biosite?", type: "boolean" },
      { name: "crcc8_fenced", label: "Fenced?", type: "choice" },
      { name: "crcc8_signed", label: "Signed", type: "choice" },
      { name: "crcc8_direction", label: "Up or Down?", type: "choice" },
      { name: "crcc8_attributea1", label: "A1" },
      { name: "crcc8_attributea2", label: "A2" },
      { name: "crcc8_attributea3", label: "A3" },
      { name: "crcc8_attributea4", label: "A4" },
      { name: "crcc8_attributea5", label: "A5" },
      { name: "crcc8_vegetationdescription", label: "Description Of Vegetation", long: true }
    ]
  };

  // Work Order table backing the "Work Order Submission" entity form.
  // *** LOW CONFIDENCE - this table was not visible to us. Confirm every
  // logical name below in the maker portal (Tables > [your Work Order
  // table] > Columns > Schema Name), then delete this comment. ***
  var WORK_ORDER_TABLE = {
    entitySet: "crcc8_workorders",
    fieldMap: {
      orderNumber: "crcc8_ordernumber",
      secondItemNumber: "crcc8_seconditemnumber",
      serialNumber: "crcc8_serialnumber",
      assetDescription: "crcc8_assetnumberdescription",
      orderTypeDescription: "crcc8_ordertypedescription",
      plannedStartIso: "crcc8_plannedstartdate",
      completeByIso: "crcc8_completebydate"
    },
    // Master-data column -> Work Order column, applied only for matched rows.
    // KP is the only one the spec calls out as mandatory; add more pairs
    // here if you add matching columns on the Work Order table.
    enrichedFieldMap: {
      crcc8_kilometerpost: "crcc8_kp"
    }
  };

  var EXPECTED_COLUMNS = [
    "orderNumber",
    "secondItemNumber",
    "serialNumber",
    "assetDescription",
    "orderTypeDescription",
    "plannedStartRaw",
    "completeByRaw"
  ];

  var COLUMN_LABELS = {
    orderNumber: "Order Number",
    secondItemNumber: "2nd Item Number",
    serialNumber: "Serial Number",
    assetDescription: "Asset Number Description",
    orderTypeDescription: "Or Ty Description",
    plannedStartRaw: "Planned Start Date",
    completeByRaw: "Complete By"
  };

  // =========================================================================
  // Parsing
  // =========================================================================

  function looksLikeHeaderRow(cells) {
    // JDE's first real column (Order Number) is always numeric; a header
    // row's first cell ("Order Number") is not.
    return !/^\d+$/.test((cells[0] || "").trim());
  }

  function parseAuDate(str) {
    if (!str) return null;
    var parts = str.trim().split("/");
    if (parts.length !== 3) return null;
    var d = parseInt(parts[0], 10);
    var m = parseInt(parts[1], 10);
    var y = parseInt(parts[2], 10);
    if (!d || !m || !y || m > 12 || d > 31) return null;
    return (
      String(y).padStart(4, "0") +
      "-" +
      String(m).padStart(2, "0") +
      "-" +
      String(d).padStart(2, "0")
    );
  }

  function normalizeSerial(v) {
    return (v || "").toString().trim().toUpperCase();
  }

  function parseJdePaste(raw) {
    var lines = raw
      .split(/\r\n|\r|\n/)
      .filter(function (l) {
        return l.trim().length > 0;
      });
    if (lines.length === 0) return [];

    var startIdx = 0;
    if (looksLikeHeaderRow(lines[0].split("\t"))) startIdx = 1;

    var rows = [];
    for (var i = startIdx; i < lines.length; i++) {
      var cells = lines[i].split("\t").map(function (c) {
        return c.trim();
      });
      var row = { lineNumber: i + 1, raw: lines[i], errors: [] };
      EXPECTED_COLUMNS.forEach(function (key, idx) {
        row[key] = cells[idx] !== undefined ? cells[idx] : "";
      });

      if (cells.length < EXPECTED_COLUMNS.length) {
        row.errors.push(
          "Expected " + EXPECTED_COLUMNS.length + " tab-separated columns, found " + cells.length + "."
        );
      }
      if (!/^\d+$/.test(row.orderNumber)) {
        row.errors.push("Order Number should be numeric.");
      }
      if (!row.serialNumber) {
        row.errors.push("Serial Number is missing.");
      }

      row.plannedStartIso = parseAuDate(row.plannedStartRaw);
      row.completeByIso = parseAuDate(row.completeByRaw);
      if (row.plannedStartRaw && !row.plannedStartIso) {
        row.errors.push('Planned Start Date "' + row.plannedStartRaw + '" is not a valid dd/mm/yyyy date.');
      }
      if (row.completeByRaw && !row.completeByIso) {
        row.errors.push('Complete By "' + row.completeByRaw + '" is not a valid dd/mm/yyyy date.');
      }

      rows.push(row);
    }
    return rows;
  }

  // =========================================================================
  // Dataverse Web API
  // =========================================================================

  var FORMATTED_VALUE_ANNOTATION = "@OData.Community.Display.V1.FormattedValue";

  function escapeODataString(v) {
    return String(v).replace(/'/g, "''");
  }

  function displayValue(rec, field) {
    var annotated = rec[field.name + FORMATTED_VALUE_ANNOTATION];
    if (annotated !== undefined && annotated !== null) return annotated;
    var raw = rec[field.name];
    if (raw === undefined || raw === null || raw === "") return "";
    if (field.type === "boolean") return raw ? "Yes" : "No";
    return raw;
  }

  var tokenPromise = null;
  function getAntiForgeryToken() {
    if (tokenPromise) return tokenPromise;
    var existing = document.querySelector('input[name="__RequestVerificationToken"]');
    if (existing && existing.value) {
      tokenPromise = Promise.resolve(existing.value);
      return tokenPromise;
    }
    tokenPromise = fetch("/_layout/tokenhtml", { credentials: "include" })
      .then(function (r) {
        return r.text();
      })
      .then(function (html) {
        var match = html.match(/value="([^"]+)"/);
        if (!match) throw new Error("Could not retrieve the anti-forgery token from /_layout/tokenhtml.");
        return match[1];
      });
    return tokenPromise;
  }

  function allAssetFields() {
    return ASSET_TABLE.primaryFields.concat(ASSET_TABLE.secondaryFields);
  }

  function fetchAssetMatches(serialNumbers) {
    var unique = Array.from(
      new Set(
        serialNumbers
          .map(function (s) {
            return (s || "").trim();
          })
          .filter(Boolean)
      )
    );
    var map = new Map();
    if (unique.length === 0) return Promise.resolve(map);

    var CHUNK = 15;
    var selectFields = [ASSET_TABLE.matchField]
      .concat(
        allAssetFields().map(function (f) {
          return f.name;
        })
      )
      .join(",");

    var chunks = [];
    for (var i = 0; i < unique.length; i += CHUNK) chunks.push(unique.slice(i, i + CHUNK));

    return chunks
      .reduce(function (chain, chunk) {
        return chain.then(function () {
          var filter = chunk
            .map(function (v) {
              return ASSET_TABLE.matchField + " eq '" + escapeODataString(v) + "'";
            })
            .join(" or ");
          var url =
            "/_api/" + ASSET_TABLE.entitySet + "?$select=" + selectFields + "&$filter=" + encodeURIComponent(filter);
          return fetch(url, {
            method: "GET",
            credentials: "include",
            headers: {
              Accept: "application/json",
              "OData-MaxVersion": "4.0",
              "OData-Version": "4.0",
              Prefer: 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
            }
          }).then(function (res) {
            if (!res.ok) {
              return res.text().then(function (text) {
                throw new Error("Master data lookup failed (HTTP " + res.status + "): " + text);
              });
            }
            return res.json().then(function (data) {
              (data.value || []).forEach(function (rec) {
                map.set(normalizeSerial(rec[ASSET_TABLE.matchField]), rec);
              });
            });
          });
        });
      }, Promise.resolve())
      .then(function () {
        return map;
      });
  }

  function buildWorkOrderPayload(row, matchedAsset) {
    var fm = WORK_ORDER_TABLE.fieldMap;
    var payload = {};
    payload[fm.orderNumber] = Number(row.orderNumber);
    payload[fm.secondItemNumber] = row.secondItemNumber;
    payload[fm.serialNumber] = row.serialNumber;
    payload[fm.assetDescription] = row.assetDescription;
    payload[fm.orderTypeDescription] = row.orderTypeDescription;
    if (row.plannedStartIso) payload[fm.plannedStartIso] = row.plannedStartIso;
    if (row.completeByIso) payload[fm.completeByIso] = row.completeByIso;

    if (matchedAsset) {
      Object.keys(WORK_ORDER_TABLE.enrichedFieldMap).forEach(function (assetField) {
        var woField = WORK_ORDER_TABLE.enrichedFieldMap[assetField];
        if (matchedAsset[assetField] !== undefined && matchedAsset[assetField] !== null) {
          payload[woField] = matchedAsset[assetField];
        }
      });
    }
    return payload;
  }

  function createWorkOrder(row, matchedAsset, token) {
    return fetch("/_api/" + WORK_ORDER_TABLE.entitySet, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        Accept: "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        __RequestVerificationToken: token
      },
      body: JSON.stringify(buildWorkOrderPayload(row, matchedAsset))
    }).then(function (res) {
      if (res.ok) return { ok: true };
      return res
        .json()
        .catch(function () {
          return null;
        })
        .then(function (body) {
          var message = body && body.error ? body.error.message : "HTTP " + res.status;
          return { ok: false, error: message };
        });
    });
  }

  // =========================================================================
  // UI
  // =========================================================================

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else if (k === "html") node.innerHTML = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) {
      if (c) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return node;
  }

  function badge(text, kind) {
    return el("span", { class: "jde-badge jde-badge-" + kind }, [text]);
  }

  function init(root) {
    var state = { rows: [], matchMap: new Map() };

    var textarea = el("textarea", {
      id: "jde-paste-textarea",
      class: "jde-textarea",
      placeholder:
        "Paste the block of work orders copied from JDE here (tab-separated, header row optional)…",
      rows: "8"
    });

    var parseBtn = el("button", { type: "button", class: "jde-btn jde-btn-primary" }, ["Parse & Match"]);
    var statusMsg = el("div", { class: "jde-status" }, []);
    var reviewSection = el("div", { class: "jde-review-section", hidden: "hidden" }, []);

    root.appendChild(
      el("div", { class: "jde-paste-match" }, [
        el("label", { class: "jde-label", for: "jde-paste-textarea" }, ["Paste Work Orders"]),
        textarea,
        el("div", { class: "jde-actions" }, [parseBtn]),
        statusMsg,
        reviewSection
      ])
    );

    parseBtn.addEventListener("click", function () {
      handleParse();
    });

    function setStatus(text, kind) {
      statusMsg.textContent = text || "";
      statusMsg.className = "jde-status" + (kind ? " jde-status-" + kind : "");
    }

    function handleParse() {
      var raw = textarea.value;
      var rows = parseJdePaste(raw);
      if (rows.length === 0) {
        setStatus("Paste at least one work order row before parsing.", "error");
        reviewSection.hidden = true;
        return;
      }

      parseBtn.disabled = true;
      setStatus("Looking up " + rows.length + " row(s) against master asset data…", "info");

      var serials = rows
        .filter(function (r) {
          return r.serialNumber;
        })
        .map(function (r) {
          return r.serialNumber;
        });

      fetchAssetMatches(serials)
        .then(function (matchMap) {
          state.rows = rows;
          state.matchMap = matchMap;
          renderReview();
          var unmatchedCount = rows.filter(function (r) {
            return r.serialNumber && !matchMap.has(normalizeSerial(r.serialNumber));
          }).length;
          if (unmatchedCount > 0) {
            setStatus(
              unmatchedCount + " of " + rows.length + " row(s) have no master-data match. Review before submitting.",
              "warn"
            );
          } else {
            setStatus("All " + rows.length + " row(s) matched. Review and submit.", "ok");
          }
        })
        .catch(function (err) {
          setStatus(err.message, "error");
        })
        .finally(function () {
          parseBtn.disabled = false;
        });
    }

    function renderReview() {
      reviewSection.innerHTML = "";
      reviewSection.hidden = false;

      var table = el("table", { class: "jde-review-table" }, []);
      var thead = el("thead", {}, []);
      var headRow = el("tr", {}, []);
      EXPECTED_COLUMNS.forEach(function (key) {
        headRow.appendChild(el("th", {}, [COLUMN_LABELS[key]]));
      });
      ASSET_TABLE.primaryFields.forEach(function (f) {
        headRow.appendChild(el("th", {}, [f.label]));
      });
      headRow.appendChild(el("th", {}, ["Match"]));
      headRow.appendChild(el("th", {}, [""]));
      thead.appendChild(headRow);
      table.appendChild(thead);

      var tbody = el("tbody", {}, []);
      var anyUnmatched = false;

      state.rows.forEach(function (row, idx) {
        var matched = row.serialNumber ? state.matchMap.get(normalizeSerial(row.serialNumber)) : null;
        var hasParseErrors = row.errors.length > 0;
        var isUnmatched = !matched && row.serialNumber && !hasParseErrors;
        if (isUnmatched) anyUnmatched = true;

        var tr = el("tr", {
          class: hasParseErrors ? "jde-row-invalid" : isUnmatched ? "jde-row-unmatched" : "jde-row-matched"
        });

        EXPECTED_COLUMNS.forEach(function (key) {
          var value = key === "plannedStartRaw" || key === "completeByRaw" ? row[key] : row[key];
          tr.appendChild(el("td", {}, [value || ""]));
        });

        ASSET_TABLE.primaryFields.forEach(function (f) {
          tr.appendChild(el("td", {}, [matched ? String(displayValue(matched, f)) : "—"]));
        });

        var matchCell = el("td", {}, []);
        if (hasParseErrors) {
          matchCell.appendChild(badge("Invalid row", "error"));
        } else if (matched) {
          matchCell.appendChild(badge("Matched", "ok"));
        } else if (row.serialNumber) {
          matchCell.appendChild(badge("No master-data match", "warn"));
        } else {
          matchCell.appendChild(badge("No Serial Number", "error"));
        }
        tr.appendChild(matchCell);

        var detailCell = el("td", {}, []);
        if (hasParseErrors || matched) {
          var toggle = el("button", { type: "button", class: "jde-link-btn" }, [
            hasParseErrors ? "Details" : "More details"
          ]);
          detailCell.appendChild(toggle);
          tr.appendChild(detailCell);

          var detailRow = el("tr", { class: "jde-detail-row", hidden: "hidden" }, []);
          var detailTd = el(
            "td",
            { colspan: String(EXPECTED_COLUMNS.length + ASSET_TABLE.primaryFields.length + 2) },
            []
          );

          if (hasParseErrors) {
            var errList = el("ul", { class: "jde-error-list" }, []);
            row.errors.forEach(function (msg) {
              errList.appendChild(el("li", {}, [msg]));
            });
            detailTd.appendChild(errList);
          } else {
            var dl = el("dl", { class: "jde-detail-list" }, []);
            ASSET_TABLE.secondaryFields.forEach(function (f) {
              var v = displayValue(matched, f);
              if (v === "") return;
              dl.appendChild(el("dt", {}, [f.label]));
              dl.appendChild(el("dd", { class: f.long ? "jde-detail-long" : "" }, [String(v)]));
            });
            if (!dl.children.length) dl.appendChild(el("dd", {}, ["No additional master-data fields set."]));
            detailTd.appendChild(dl);
          }

          detailRow.appendChild(detailTd);
          toggle.addEventListener("click", function () {
            detailRow.hidden = !detailRow.hidden;
            toggle.textContent = detailRow.hidden ? (hasParseErrors ? "Details" : "More details") : "Hide";
          });
        } else {
          tr.appendChild(detailCell);
        }

        tbody.appendChild(tr);
        if (hasParseErrors || matched) tbody.appendChild(detailRow);
      });

      table.appendChild(tbody);
      reviewSection.appendChild(table);

      var overrideWrap = el("label", { class: "jde-override" }, []);
      var overrideCheckbox = el("input", { type: "checkbox", id: "jde-override-checkbox" });
      overrideWrap.appendChild(overrideCheckbox);
      overrideWrap.appendChild(
        document.createTextNode(" Submit anyway, even though some Serial Numbers have no master-data match")
      );

      var submitBtn = el("button", { type: "button", class: "jde-btn jde-btn-primary" }, [
        "Create Work Order(s)"
      ]);
      var resultMsg = el("div", { class: "jde-status" }, []);

      var actionsWrap = el("div", { class: "jde-submit-actions" }, []);
      if (anyUnmatched) actionsWrap.appendChild(overrideWrap);
      actionsWrap.appendChild(submitBtn);
      reviewSection.appendChild(actionsWrap);
      reviewSection.appendChild(resultMsg);

      function updateSubmitEnabled() {
        var blockingInvalid = state.rows.some(function (r) {
          return r.errors.length > 0;
        });
        submitBtn.disabled = blockingInvalid || (anyUnmatched && !overrideCheckbox.checked);
      }
      overrideCheckbox.addEventListener("change", updateSubmitEnabled);
      updateSubmitEnabled();

      submitBtn.addEventListener("click", function () {
        submitBtn.disabled = true;
        resultMsg.textContent = "";
        var validRows = state.rows.filter(function (r) {
          return r.errors.length === 0;
        });

        getAntiForgeryToken()
          .then(function (token) {
            var succeeded = 0;
            var failed = [];
            return validRows
              .reduce(function (chain, row) {
                return chain.then(function () {
                  var matched = row.serialNumber ? state.matchMap.get(normalizeSerial(row.serialNumber)) : null;
                  return createWorkOrder(row, matched, token).then(function (result) {
                    resultMsg.textContent =
                      "Submitting " + (succeeded + failed.length + 1) + " of " + validRows.length + "…";
                    if (result.ok) succeeded++;
                    else failed.push({ row: row, error: result.error });
                  });
                });
              }, Promise.resolve())
              .then(function () {
                return { succeeded: succeeded, failed: failed };
              });
          })
          .then(function (summary) {
            if (summary.failed.length === 0) {
              resultMsg.className = "jde-status jde-status-ok";
              resultMsg.textContent = "Created " + summary.succeeded + " work order(s) successfully.";
            } else {
              resultMsg.className = "jde-status jde-status-error";
              resultMsg.textContent =
                "Created " +
                summary.succeeded +
                " of " +
                validRows.length +
                " work order(s). Failures: " +
                summary.failed
                  .map(function (f) {
                    return "Order " + f.row.orderNumber + " (" + f.error + ")";
                  })
                  .join("; ");
            }
          })
          .catch(function (err) {
            resultMsg.className = "jde-status jde-status-error";
            resultMsg.textContent = err.message;
          })
          .finally(function () {
            submitBtn.disabled = false;
          });
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.getElementById("jde-paste-match-root");
    if (root) init(root);
  });
})();
