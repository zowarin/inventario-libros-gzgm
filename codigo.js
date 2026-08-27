const VISION_API_KEY = 'AIzaSyCiBdtY0d-plSPz9xwaIsXcnSpTh8X3dOs';
const FOLDER_ID = "16aKGCr8pAeHKeP2Gs8xj6NvA_RmhPajp";

function doPost(e) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const params = JSON.parse(e.postData.contents);
  const action = params.action;

  // === OCR ===
  if (action === 'ocr') {
    if (!params.fotoBase64) {
      return jsonResponse({ status: "ERROR", message: "No se proporcionó imagen para OCR" });
    }
    const ocrResult = analizarImagenOCR(params.fotoBase64);

    if (ocrResult.exito) {
      return jsonResponse({
        status: "OK",
        visionData: ocrResult.visionData
      });
    } else {
      return jsonResponse({ status: "ERROR", message: ocrResult.mensaje });
    }
  }

  // === CREATE PINTURA ===
  if (action === "create") {
    const sheet = ss.getSheetByName('InvetarioPinturas');
    const lastRow = sheet.getLastRow();
    let newId = 1;

    if (lastRow > 1) {
      const lastId = sheet.getRange(lastRow, 1).getValue();
      newId = lastId + 1;
    }

    let imageUrl = "";
    if (params.fotoBase64) {
      imageUrl = saveImageToDrive(params.fotoBase64, 'pintura_' + newId);
    }

    sheet.appendRow([
      newId,
      params.title || "",
      params.autor || "",
      params.year || "",
      params.tecnic || "",
      params.size || "",
      imageUrl,
      new Date(),
      params.awared || "",
      params.type || ""
    ]);

    return jsonResponse({ status: "OK", message: "Pintura creada", id: newId, imageUrl: imageUrl });
  }

  // === CREATE LIBRO ===
  if (action === "create-book") {
    let sheet = ss.getSheetByName('InventarioLibros');

    // Crear hoja si no existe
    if (!sheet) {
      sheet = ss.insertSheet('InventarioLibros');
      sheet.appendRow(['ID', 'Titulo', 'Foto', 'Fecha', 'Ubicacion']);
    }

    const lastRow = sheet.getLastRow();
    let newId = 1;

    if (lastRow > 1) {
      const lastId = sheet.getRange(lastRow, 1).getValue();
      newId = lastId + 1;
    }

    let imageUrl = "";
    if (params.fotoBase64) {
      imageUrl = saveImageToDrive(params.fotoBase64, 'libro_' + newId);
    }

    sheet.appendRow([
      newId,
      params.title || "",
      imageUrl,
      new Date(),
      params.awared || ""
    ]);

    return jsonResponse({ status: "OK", message: "Libro creado", id: newId, imageUrl: imageUrl });
  }

  // === READ ===
  if (action === "read") {
    const sheet = ss.getSheetByName('InvetarioPinturas');
    const rows = sheet.getDataRange().getValues();
    rows.shift(); // Quitar headers

    const data = rows.map(r => ({
      id: r[0],
      title: r[1],
      autor: r[2],
      year: r[3],
      tecnic: r[4],
      size: r[5],
      foto: r[6],
      created: r[7],
      awared: r[8],
      type: r[9]
    }));

    return jsonResponse({ status: "OK", items: data });
  }

  return jsonResponse({ status: "ERROR", message: "Acción no válida version 2: " + action });
}

function saveImageToDrive(base64Data, prefix) {
  try {
    const folder = DriveApp.getFolderById(FOLDER_ID);
    const base64Clean = base64Data.replace(/^data:image\/\w+;base64,/, '');

    let mimeType = 'image/jpeg';
    let extension = 'jpg';

    if (base64Data.includes('data:image/png')) {
      mimeType = 'image/png';
      extension = 'png';
    } else if (base64Data.includes('data:image/webp')) {
      mimeType = 'image/webp';
      extension = 'webp';
    }

    const blob = Utilities.newBlob(
      Utilities.base64Decode(base64Clean),
      mimeType,
      `${prefix}_${new Date().getTime()}.${extension}`
    );

    const file = folder.createFile(blob);
    file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

    return `https://drive.google.com/uc?id=${file.getId()}`;
  } catch (error) {
    Logger.log('Error guardando imagen: ' + error.toString());
    return "";
  }
}

function jsonResponse(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function analizarImagenOCR(base64Data) {
  try {
    const base64Clean = base64Data.replace(/^data:image\/\w+;base64,/, '');
    const visionUrl = `https://vision.googleapis.com/v1/images:annotate?key=${VISION_API_KEY}`;

    const payload = {
      requests: [{
        image: { content: base64Clean },
        features: [{ type: 'TEXT_DETECTION' }]
      }]
    };

    const response = UrlFetchApp.fetch(visionUrl, {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    const result = JSON.parse(response.getContentText());

    if (result.error) {
      return { exito: false, mensaje: 'Error en Vision API: ' + result.error.message };
    }

    const visionData = result.responses[0];

    if (visionData.textAnnotations && visionData.textAnnotations.length > 0) {
      return { exito: true, visionData: visionData };
    }

    return { exito: false, mensaje: 'No se detectó texto en la imagen' };

  } catch (error) {
    return { exito: false, mensaje: 'Error al procesar: ' + error.toString() };
  }
}
