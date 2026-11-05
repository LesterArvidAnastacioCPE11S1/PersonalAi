package com.personalai.app;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Menu;
import android.view.MenuItem;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.HashMap;
import java.util.Map;

public class MainActivity extends Activity {

    private static final int FILE_CHOOSER = 1001;
    private static final String PREFS = "personalai";

    private SharedPreferences prefs;
    private WebView webView;
    private ValueCallback<Uri[]> fileCallback;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        String server = prefs.getString("server", "");
        String code = prefs.getString("code", "");

        if (server.isEmpty()) {
            showSetup("");
        } else {
            openChat(server, code);
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void showSetup(String error) {
        releaseWebView();

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.rgb(11, 11, 11));

        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(24), dp(40), dp(24), dp(24));
        scroll.addView(box, new ScrollView.LayoutParams(-1, -2));

        TextView title = label("PersonalAI", 26, Color.rgb(242, 242, 242));
        title.setTypeface(title.getTypeface(), Typeface.BOLD);
        box.addView(title);

        TextView note = label(
            "Enter the address shown in the app window on the PC, then the access code. Both devices must be on the same Wi-Fi.",
            14,
            Color.rgb(154, 154, 154)
        );
        LinearLayout.LayoutParams noteParams = new LinearLayout.LayoutParams(-1, -2);
        noteParams.topMargin = dp(8);
        noteParams.bottomMargin = dp(24);
        box.addView(note, noteParams);

        box.addView(
            label("Server address", 11, Color.rgb(138, 138, 138)),
            new LinearLayout.LayoutParams(-1, -2)
        );

        EditText serverInput = input();
        serverInput.setHint("http://192.168.1.10:8000");
        serverInput.setInputType(
            InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI
        );
        serverInput.setText(prefs.getString("server", ""));
        box.addView(serverInput, new LinearLayout.LayoutParams(-1, -2));

        TextView codeLabel = label("Access code", 11, Color.rgb(138, 138, 138));
        LinearLayout.LayoutParams codeLabelParams = new LinearLayout.LayoutParams(-1, -2);
        codeLabelParams.topMargin = dp(16);
        box.addView(codeLabel, codeLabelParams);

        EditText codeInput = input();
        codeInput.setHint("ABCDE-FGHIJ");
        codeInput.setInputType(
            InputType.TYPE_CLASS_TEXT
                | InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS
                | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
        );
        codeInput.setText(prefs.getString("code", ""));
        box.addView(codeInput, new LinearLayout.LayoutParams(-1, -2));

        if (!error.isEmpty()) {
            TextView errorView = label(error, 13, Color.rgb(255, 143, 143));
            LinearLayout.LayoutParams errorParams = new LinearLayout.LayoutParams(-1, -2);
            errorParams.topMargin = dp(14);
            box.addView(errorView, errorParams);
        }

        Button connect = new Button(this);
        connect.setText("Connect");
        connect.setAllCaps(false);
        LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(-1, dp(52));
        buttonParams.topMargin = dp(24);
        box.addView(connect, buttonParams);

        connect.setOnClickListener(view -> {
            String server = normalizeServer(serverInput.getText().toString());
            String code = normalizeCode(codeInput.getText().toString());

            if (server.isEmpty()) {
                showSetup("Enter the PC address.");
                return;
            }

            if (code.length() < 6) {
                showSetup("Access code must be at least 6 characters.");
                return;
            }

            prefs.edit()
                .putString("server", server)
                .putString("code", code)
                .apply();

            openChat(server, code);
        });

        setContentView(scroll);
    }

    private TextView label(String text, int size, int color) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);

        if (size == 11) {
            view.setAllCaps(true);
            view.setLetterSpacing(0.06f);
        }

        return view;
    }

    private EditText input() {
        EditText view = new EditText(this);
        view.setSingleLine(true);
        view.setTextSize(16);
        view.setTextColor(Color.rgb(244, 244, 244));
        view.setHintTextColor(Color.rgb(110, 110, 110));
        return view;
    }

    private String normalizeServer(String value) {
        String server = value.trim();

        if (server.isEmpty()) {
            return "";
        }

        if (
            !server.startsWith("http://")
            && !server.startsWith("https://")
        ) {
            server = "http://" + server;
        }

        while (server.endsWith("/")) {
            server = server.substring(0, server.length() - 1);
        }

        return server;
    }

    private String normalizeCode(String value) {
        StringBuilder code = new StringBuilder();

        for (char character : value.toCharArray()) {
            if (Character.isLetterOrDigit(character)) {
                code.append(Character.toUpperCase(character));
            }
        }

        return code.toString();
    }

    private void openChat(String server, String code) {
        releaseWebView();

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(11, 11, 11));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setTextZoom(100);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        cookies.setAcceptThirdPartyCookies(webView, false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return handleUrl(request.getUrl(), server);
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(
                WebView view,
                ValueCallback<Uri[]> callback,
                FileChooserParams params
            ) {
                if (fileCallback != null) {
                    fileCallback.onReceiveValue(null);
                }

                fileCallback = callback;

                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);

                try {
                    startActivityForResult(
                        Intent.createChooser(intent, "Attach file"),
                        FILE_CHOOSER
                    );
                } catch (Exception error) {
                    fileCallback = null;
                    Toast.makeText(
                        MainActivity.this,
                        "No file picker available.",
                        Toast.LENGTH_SHORT
                    ).show();
                    return false;
                }

                return true;
            }
        });

        setContentView(webView);

        Map<String, String> headers = new HashMap<>();

        if (!code.isEmpty()) {
            headers.put("X-PAI-Token", code);
        }

        webView.loadUrl(server + "/", headers);
    }

    private boolean handleUrl(Uri uri, String server) {
        String scheme = uri.getScheme();

        if ("http".equals(scheme) || "https".equals(scheme)) {
            String host = uri.getHost();
            String baseHost = Uri.parse(server).getHost();

            if (host != null && host.equals(baseHost)) {
                return false;
            }
        }

        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception ignored) {
            ignored.printStackTrace();
        }

        return true;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER) {
            if (fileCallback == null) {
                return;
            }

            Uri[] result = null;

            if (resultCode == RESULT_OK && data != null) {
                ClipData clip = data.getClipData();

                if (clip != null) {
                    result = new Uri[clip.getItemCount()];

                    for (int index = 0; index < clip.getItemCount(); index++) {
                        result[index] = clip.getItemAt(index).getUri();
                    }
                } else if (data.getData() != null) {
                    result = new Uri[]{data.getData()};
                }
            }

            fileCallback.onReceiveValue(result);
            fileCallback = null;
            return;
        }

        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        menu.add(0, 1, 0, "Reload");
        menu.add(0, 2, 1, "Change server");
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == 1) {
            if (webView != null) {
                webView.reload();
            }

            return true;
        }

        if (item.getItemId() == 2) {
            showSetup("");
            return true;
        }

        return super.onOptionsItemSelected(item);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }

        super.onBackPressed();
    }

    @Override
    protected void onPause() {
        if (webView != null) {
            webView.onPause();
            CookieManager.getInstance().flush();
        }

        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();

        if (webView != null) {
            webView.onResume();
        }
    }

    @Override
    protected void onDestroy() {
        releaseWebView();
        super.onDestroy();
    }

    private void releaseWebView() {
        if (webView == null) {
            return;
        }

        ViewGroup parent = (ViewGroup) webView.getParent();

        if (parent != null) {
            parent.removeView(webView);
        }

        webView.stopLoading();
        webView.loadUrl("about:blank");
        webView.removeAllViews();
        webView.destroy();
        webView = null;
    }
}
