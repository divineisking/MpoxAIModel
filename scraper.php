<?php
require __DIR__ . '/vendor/autoload.php';

// Configuration
$config = [
    'base_url' => 'https://ncdc.gov.ng',
    'reports_path' => '/diseases/sitreps/',
    'query_params' => [
        'cat' => 8,  // Monkeypox category ID
        'name' => 'An Update of Monkeypox Outbreak in Nigeria'
    ],
    'save_dir' => __DIR__ . '/pdfs/',
    'log_file' => __DIR__ . '/scraper.log',
    'timeout' => 30,
    'delay' => 5 // Seconds between requests
];

// Setup Guzzle Client
$client = new \GuzzleHttp\Client([
    'base_uri' => $config['base_url'],
    'verify' => false, // Disable SSL verification (use only for testing)
    'headers' => [
        'User-Agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept' => 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    ],
    'allow_redirects' => true,
    'timeout' => $config['timeout']
]);

// Ensure directories exist
if (!file_exists($config['save_dir'])) {
    mkdir($config['save_dir'], 0755, true);
}

try {
    // Step 1: Fetch the reports page
    $response = $client->get($config['reports_path'], [
        'query' => $config['query_params']
    ]);
    $html = (string)$response->getBody();

    // Step 2: Parse PDF links
    $dom = new DOMDocument();
    @$dom->loadHTML($html);
    $xpath = new DOMXPath($dom);

    $links = $xpath->query('//a[contains(@class, "black-text") and contains(@href, ".pdf")]');

    $pdfQueue = [];
    foreach ($links as $link) {
        $pdfQueue[] = [
            'uri' => $link->getAttribute('href'),
            'filename' => $link->getAttribute('download') ?: basename($link->getAttribute('href'))
        ];
    }

    // Step 3: Process downloads
    $total = count($pdfQueue);
    $downloaded = 0;
    
    echo "Found {$total} PDF reports\n";
    
    foreach ($pdfQueue as $index => $pdf) {
        $filePath = $config['save_dir'] . $pdf['filename'];
        $progress = "[ " . ($index + 1) . "/{$total} ] ";
        
        if (file_exists($filePath)) {
            echo $progress . "Skipping existing: {$pdf['filename']}\n";
            continue;
        }

        echo $progress . "Downloading {$pdf['filename']}... ";

        try {
            $client->request('GET', $pdf['uri'], [
                'sink' => $filePath,
                'on_stats' => function (\GuzzleHttp\TransferStats $stats) use (&$downloaded) {
                    if ($stats->hasResponse() && $stats->getResponse()->getStatusCode() === 200) {
                        $downloaded++;
                    }
                }
            ]);

            echo "✓\n";
        } catch (\GuzzleHttp\Exception\RequestException $e) {
            echo "✗ Failed: " . $e->getMessage() . "\n";
            file_put_contents(
                $config['log_file'],
                date('[Y-m-d H:i:s] ') . "{$pdf['filename']} - {$e->getMessage()}\n",
                FILE_APPEND
            );
        }

        // Respectful delay between requests
        if ($index < ($total - 1)) {
            sleep($config['delay']);
        }
    }

    echo "\nDownload complete! {$downloaded}/{$total} new files downloaded\n";
    echo "Saved to: {$config['save_dir']}\n";

} catch (\Exception $e) {
    die("Fatal error: " . $e->getMessage());
}