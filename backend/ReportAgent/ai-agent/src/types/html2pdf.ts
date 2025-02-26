declare module "html2pdf.js" {
  interface Html2PdfOptions {
    margin?: number | number[];
    filename?: string;
    image?: { type?: string; quality?: number };
    html2canvas?: {
      scale?: number;
      logging?: boolean;
      useCORS?: boolean;
    };
    jsPDF?: {
      orientation?: string;
      unit?: string;
      format?: string | number[];
      putOnlyUsedFonts?: boolean;
      compressPDF?: boolean;
    };
  }

  interface Html2Pdf {
    from(element: HTMLElement | string): this;
    set(options: Html2PdfOptions): this;
    toPdf(): Promise<void>;
    save(filename?: string): Promise<void>;
    output(
      type: string,
      options?: string
    ): Promise<string | Uint8Array | ArrayBuffer | Blob>;
  }

  function html2pdf(): Html2Pdf;

  export = html2pdf;
}
