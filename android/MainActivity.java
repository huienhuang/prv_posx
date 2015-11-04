package forest.forestv2;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.support.v7.app.ActionBarActivity;
import android.util.Base64;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.CookieSyncManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import com.google.android.gms.common.api.CommonStatusCodes;
import com.google.android.gms.samples.vision.barcodereader.BarcodeCaptureActivity;
import com.google.android.gms.vision.barcode.Barcode;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;


public class MainActivity extends ActionBarActivity {
    private static final String TAG = "FOREST_MAIN";

    private WebView m_webview;
    private ValueCallback<Uri> m_upload_msg;

    private final int REQUEST_IMAGE_CAPTURE = 1000;
    private static final int RC_BARCODE_CAPTURE = 9001;

    private File m_cam_img_file = null;
    private String m_barcode_data = null;

    private CookieManager m_cookie_mgr = null;

    private final String HOME_URL_PROD = "http://10.0.1.188/posx/mobile";
    private final String HOME_URL_DEV = "http://10.0.0.70/posx/mobile";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        getSupportActionBar().hide();

        CookieSyncManager.createInstance(this);
        m_cookie_mgr = CookieManager.getInstance();
        m_cookie_mgr.removeAllCookie();

        m_webview = (WebView)findViewById(R.id.webView);
        m_webview.setWebViewClient(new WebViewClient());
        WebSettings settings = m_webview.getSettings();
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setJavaScriptEnabled(true);
        m_webview.addJavascriptInterface(new WebAppInterface(this), "Android");

        m_webview.loadUrl(HOME_URL_PROD);




    }

    @Override
    protected void onDestroy() {
        m_cookie_mgr.removeAllCookie();

        super.onDestroy();
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        // Inflate the menu; this adds items to the action bar if it is present.
        getMenuInflater().inflate(R.menu.menu_main, menu);
        return true;
    }

    @Override
    public void onBackPressed() {
        m_webview.loadUrl(HOME_URL_PROD);

        //super.onBackPressed();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQUEST_IMAGE_CAPTURE) {
            if(m_cam_img_file == null) return;

            m_webview.loadUrl("javascript:window.OnPictureReady && window.setTimeout(window.OnPictureReady, 0)");

        } else if (requestCode == RC_BARCODE_CAPTURE) {
            m_barcode_data = null;

            if (resultCode != CommonStatusCodes.SUCCESS || data == null) return;

            Barcode barcode = data.getParcelableExtra(BarcodeCaptureActivity.BarcodeObject);
            m_barcode_data = barcode.rawValue;

            m_webview.loadUrl("javascript:window.OnBarcodeReady && window.setTimeout(window.OnBarcodeReady, 0)");

        }else {
            super.onActivityResult(requestCode, resultCode, data);

        }

    }

    private void open_barcode_scanner(long barcode_timeout) {
        Intent intent = new Intent(this, BarcodeCaptureActivity.class);
        intent.putExtra(BarcodeCaptureActivity.AutoFocus, true);
        intent.putExtra(BarcodeCaptureActivity.UseFlash, false);
        intent.putExtra(BarcodeCaptureActivity.BarcodeTimeout, barcode_timeout);

        startActivityForResult(intent, RC_BARCODE_CAPTURE);

        //Log.d(TAG, "open_barcode_scanner");
    }

    public static Matrix getMatrix(int orientation)  {
        Matrix matrix = new Matrix();
        switch (orientation) {
            case ExifInterface.ORIENTATION_FLIP_HORIZONTAL:
                matrix.setScale(-1, 1);
                break;
            case ExifInterface.ORIENTATION_ROTATE_180:
                matrix.setRotate(180);
                break;
            case ExifInterface.ORIENTATION_FLIP_VERTICAL:
                matrix.setRotate(180);
                matrix.postScale(-1, 1);
                break;
            case ExifInterface.ORIENTATION_TRANSPOSE:
                matrix.setRotate(90);
                matrix.postScale(-1, 1);
                break;
            case ExifInterface.ORIENTATION_ROTATE_90:
                matrix.setRotate(90);
                break;
            case ExifInterface.ORIENTATION_TRANSVERSE:
                matrix.setRotate(-90);
                matrix.postScale(-1, 1);
                break;
            case ExifInterface.ORIENTATION_ROTATE_270:
                matrix.setRotate(-90);
                break;
            default:
                return null;
        }

        return matrix;
    }

    public class WebAppInterface {
        Context m_ctx;

        WebAppInterface(Context c) {
            m_ctx = c;
        }


        @JavascriptInterface
        public void setDevMode() {
            m_webview.loadUrl(HOME_URL_DEV);
        }

        @JavascriptInterface
        public void scanBarcode() {
            m_barcode_data = null;

            open_barcode_scanner(250);
        }

        @JavascriptInterface
        public void scanBarcodeEx(long barcode_timeout) {
            m_barcode_data = null;

            open_barcode_scanner(barcode_timeout);
        }

        @JavascriptInterface
        public String getBarcode() {
            String ret = m_barcode_data;
            m_barcode_data = null;
            return ret;
        }

        @JavascriptInterface
        public void takePicture() {
            m_cam_img_file = null;

            Intent takePictureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);

            if (takePictureIntent.resolveActivity(getPackageManager()) != null) {
                File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES);

                try {
                    m_cam_img_file = File.createTempFile("CAM_IMG_", ".jpg", dir);
                    m_cam_img_file.deleteOnExit();
                    takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, Uri.fromFile(m_cam_img_file));
                    startActivityForResult(takePictureIntent, REQUEST_IMAGE_CAPTURE);

                } catch (IOException e) {
                    //Log.d("PK", ">>>>>>>>>>>ERROR1");

                }

            }
        }

        @JavascriptInterface
        public String getPicture() {
            if(m_cam_img_file == null) return null;

            String ret = null;
            try {
                ExifInterface exif;
                exif = new ExifInterface(m_cam_img_file.getAbsolutePath());
                int orientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_UNDEFINED);
                Matrix matrix = getMatrix(orientation);

                Bitmap img = BitmapFactory.decodeStream(new FileInputStream(m_cam_img_file));

                int w = img.getWidth();
                int h = img.getHeight();
                float nw = w;
                float nh = h;
                if(w >= h) {
                    if(w > 1200) {
                        nh = nh / nw * 1200;
                        nw = 1200;
                    }
                } else {
                    if(h > 1200) {
                        nw = nw / nh * 1200;
                        nh = 1200;
                    }
                }

                img = Bitmap.createScaledBitmap(img, (int) nw, (int) nh, true);

                if(matrix != null)
                    img = Bitmap.createBitmap(img, 0, 0, img.getWidth(), img.getHeight(), matrix, true);

                ByteArrayOutputStream os = new ByteArrayOutputStream();
                img.compress(Bitmap.CompressFormat.JPEG, 85, os);

                ret = Base64.encodeToString(os.toByteArray(), Base64.DEFAULT);

            } catch(IOException ex) {
                //Log.d("PK", ">>>>>>>>>>>ERROR2");

            } finally {
                m_cam_img_file.delete();
                m_cam_img_file = null;

            }

            return ret;
        }

    }


}
