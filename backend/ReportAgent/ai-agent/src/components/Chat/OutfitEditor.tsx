import React, { useState, useRef, useEffect, useId } from 'react';
import styles from './OutfitEditor.module.scss';
import { Upload, Trash2, ThermometerSnowflake, Wand2 } from 'lucide-react';

interface Coordinate {
  x: number;
  y: number;
  size: number;
}

const OutfitEditor: React.FC = () => {
  // 고유 ID 생성
  const uniqueId = useId();
  const inputId = `image-upload-${uniqueId}`;

  // State management
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>('');
  const [negativePrompt, setNegativePrompt] = useState<string>('deformed, distorted, low quality');
  const [brushSize, setBrushSize] = useState<number>(20);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [brushCoordinates, setBrushCoordinates] = useState<Coordinate[]>([]);
  const [isPainting, setIsPainting] = useState<boolean>(false);
  
  // Advanced settings
  const [steps, setSteps] = useState<number>(20);
  const [guidance, setGuidance] = useState<number>(7.5);
  const [seed, setSeed] = useState<number>(42);
  const [useAnimeSeg, setUseAnimeSeg] = useState<boolean>(false);
  const [smoothMask, setSmoothMask] = useState<boolean>(true);
  const [morphOperation, setMorphOperation] = useState<string>("none");
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);
  
  const [error, setError] = useState<string | null>(null);
  
  // References
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  
  // Gradio API endpoint
  const API_DOMAIN = 'https://3e1a58ec46098d8838.gradio.live/';
  const API_URL = `${API_DOMAIN}api/predict`;
  
  // Check server on component mount
  useEffect(() => {
    const checkServer = async () => {
      try {
        const response = await fetch(API_DOMAIN);
        if (response.ok) {
          console.log('Gradio server is running');
        }
      } catch (error) {
        console.error('Cannot connect to Gradio server:', error);
        setError('Unable to connect to the Gradio server. Please make sure it is running.');
      }
    };
    
    checkServer();
  }, []);
  
  // Handle image upload
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setOriginalImage(dataUrl);
      setResultImage(null);
      setBrushCoordinates([]);
      setError(null);
      
      // Set up canvas after image load
      const img = new Image();
      img.onload = () => {
        if (canvasRef.current && maskCanvasRef.current) {
          imageRef.current = img;
          
          // Original image canvas
          const canvas = canvasRef.current;
          canvas.width = img.width;
          canvas.height = img.height;
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);
          }
          
          // Mask canvas
          const maskCanvas = maskCanvasRef.current;
          maskCanvas.width = img.width;
          maskCanvas.height = img.height;
          const maskCtx = maskCanvas.getContext('2d');
          if (maskCtx) {
            maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
            maskCtx.fillStyle = 'rgba(0, 0, 0, 0)';
            maskCtx.fillRect(0, 0, maskCanvas.width, maskCanvas.height);
          }
        }
      };
      img.src = dataUrl;
    };
    reader.readAsDataURL(file);
  };
  
  // Draw brush on canvas for the mask
  const drawBrushOnCanvas = (x: number, y: number) => {
    if (!maskCanvasRef.current) return;
    
    const canvas = maskCanvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // 좌표가 캔버스 범위 내에 있는지 확인
    if (x < 0 || y < 0 || x > canvas.width || y > canvas.height) return;
    
    // Draw white area for mask
    ctx.beginPath();
    ctx.globalAlpha = 1.0; // 완전 불투명하게 설정
    ctx.fillStyle = 'white';
    ctx.arc(x, y, brushSize, 0, Math.PI * 2);
    ctx.fill();
    
    // Save brush coordinates
    setBrushCoordinates(prev => [...prev, { x, y, size: brushSize }]);
    
    // Overlay the mask on top of the original image
    updateOverlay();
  };
  
  // Update the overlay
  const updateOverlay = () => {
    if (!canvasRef.current || !maskCanvasRef.current || !imageRef.current) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Redraw the original image
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(imageRef.current, 0, 0);
    
    // Draw the mask overlay with semi-transparent red
    ctx.save();
    ctx.globalAlpha = 0.4; // 투명도 조정
    ctx.globalCompositeOperation = 'source-atop'; // 마스크가 이미지 위에만 적용되도록
    ctx.fillStyle = 'rgba(241, 238, 238, 0.5)';
    
    // 마스크 캔버스의 내용을 가져와서 마스크 영역만 빨간색으로 표시
    const maskCanvas = maskCanvasRef.current;
    const maskCtx = maskCanvas.getContext('2d', { willReadFrequently: true });
    if (maskCtx) {
      const maskData = maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = maskCanvas.width;
      tempCanvas.height = maskCanvas.height;
      const tempCtx = tempCanvas.getContext('2d');
      
      if (tempCtx) {
        // 마스크 데이터를 빨간색으로 변환
        const imgData = tempCtx.createImageData(maskCanvas.width, maskCanvas.height);
        for (let i = 0; i < maskData.data.length; i += 4) {
          if (maskData.data[i] > 0) { // 흰색 영역이면
            imgData.data[i] = 255;     // R
            imgData.data[i+1] = 0;     // G
            imgData.data[i+2] = 0;     // B
            imgData.data[i+3] = 128;   // A (반투명)
          }
        }
        tempCtx.putImageData(imgData, 0, 0);
        ctx.drawImage(tempCanvas, 0, 0);
      }
    }
    
    ctx.restore();
  };
  
  // 캔버스 크기 조정 및 관리
  const [canvasScale, setCanvasScale] = useState(1);
  
  // 이미지 로드 후 캔버스 스케일 계산
  useEffect(() => {
    if (canvasRef.current && imageRef.current && originalImage) {
      const parentWidth = canvasRef.current.parentElement?.clientWidth || 0;
      if (parentWidth > 0 && imageRef.current.width > 0) {
        // 부모 요소의 너비에 맞게 스케일 설정 (원본보다 커지지 않도록 제한)
        const newScale = Math.min(parentWidth / imageRef.current.width, 1);
        setCanvasScale(newScale);
      }
    }
  }, [originalImage]);
  
  // Mouse event handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsPainting(true);
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    // 실제 캔버스 크기와 표시되는 크기의 비율 계산
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    // 실제 캔버스 내 좌표 계산
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    
    drawBrushOnCanvas(x, y);
  };
  
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isPainting || !canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    // 실제 캔버스 크기와 표시되는 크기의 비율 계산
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    // 실제 캔버스 내 좌표 계산
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    
    drawBrushOnCanvas(x, y);
  };
  
  const handleMouseUp = () => {
    setIsPainting(false);
  };
  
  // Clear mask
  const clearMask = () => {
    if (!maskCanvasRef.current || !canvasRef.current || !imageRef.current) return;
    
    const maskCanvas = maskCanvasRef.current;
    const maskCtx = maskCanvas.getContext('2d');
    if (!maskCtx) return;
    
    // Clear the mask canvas
    maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
    
    // Redraw the original image
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(imageRef.current, 0, 0);
    }
    
    setBrushCoordinates([]);
  };
  
  // Run inpainting
  const handleProcessImage = async () => {
    if (!originalImage || !maskCanvasRef.current) {
      setError('You need both image and mask.');
      return;
    }
    
    if (brushCoordinates.length === 0) {
      setError('Please select the area you want to edit.');
      return;
    }
    
    setIsProcessing(true);
    setError(null);
    
    try {
      // Convert the original image to data URL
      const inputImage = originalImage;
      
      // Get the mask image from the mask canvas
      const maskCanvas = maskCanvasRef.current;
      const maskDataUrl = maskCanvas.toDataURL('image/png');
      
      // Send data to the Gradio API
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },

        body: JSON.stringify({
          data: [
            inputImage,   // Base64 image
            maskDataUrl,  // Base64 mask
            prompt,       // string
            negativePrompt,  // string
            steps,        // number
            guidance,     // number
            seed,         // number
            useAnimeSeg,  // boolean
            smoothMask,   // boolean
            morphOperation, // string
            "runwayml/stable-diffusion-inpainting" // Another inpainting model
          ]
        })
      });
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      // Process API response
      if (result.data) {
        setResultImage(result.data);
      } else {
        throw new Error('No valid result was returned from the API.');
      }
    } catch (error) {
      console.error('Error during image processing:', error);
      setError(`Error occurred while processing: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Continue editing with the result image
  const continueEditingWithResult = () => {
    if (!resultImage) return;
    
    setOriginalImage(resultImage);
    setResultImage(null);
    
    // Re-initialize canvas with the new image
    const img = new Image();
    img.onload = () => {
      imageRef.current = img;
      
      if (canvasRef.current && maskCanvasRef.current) {
        // Original image canvas
        const canvas = canvasRef.current;
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0);
        }
        
        // Mask canvas
        const maskCanvas = maskCanvasRef.current;
        maskCanvas.width = img.width;
        maskCanvas.height = img.height;
        const maskCtx = maskCanvas.getContext('2d');
        if (maskCtx) {
          maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
        }
        
        // 스케일 조정 필요 없음 - useEffect에서 자동으로 처리
        setBrushCoordinates([]);
      }
    };
    img.src = resultImage;
  };
  
  // Generate random seed
  const generateRandomSeed = () => {
    setSeed(Math.floor(Math.random() * 1000000));
  };
  
  return (
    <div className={styles.outfitEditor}>
      <div className={styles.header}>
        <h2>Anime Outfit Editor</h2>
        <p>Outfit editing using SAM + Stable Diffusion Inpainting</p>
      </div>
      
      <div className={styles.content}>
        {error && <div className={styles.errorMessage}>{error}</div>}
        
        <section className={styles.uploadSection}>
          <input
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            id={inputId}
            className={styles.hiddenInput}
          />
          <label htmlFor={inputId} className={styles.uploadButton}>
            <Upload size={20} />
            Upload Character Image
          </label>
        </section>
        
        {originalImage && (
          <section className={styles.editorSection}>
            <div className={styles.canvasContainer}>
              <div 
                className={styles.canvasWrapper}
                style={{
                  width: '100%',
                  height: 'auto'
                }}
              >
                <canvas
                  ref={canvasRef}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                  className={styles.canvas}
                />
                <canvas 
                  ref={maskCanvasRef} 
                  className={styles.maskCanvas}
                />
              </div>
              <div className={styles.canvasControls}>
                <div className={styles.controlGroup}>
                  <label>Brush size: {brushSize}px</label>
                  <input
                    type="range"
                    min="5"
                    max="100"
                    value={brushSize}
                    onChange={(e) => setBrushSize(parseInt(e.target.value))}
                    className={styles.slider}
                  />
                </div>
                <button onClick={clearMask} className={styles.secondaryButton}>
                  <Trash2 size={16} />
                  Clear Mask
                </button>
              </div>
            </div>
            
            <div className={styles.promptSection}>
              <div className={styles.controlGroup}>
                <label>Prompt:</label>
                <input
                  type="text"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe the desired outfit (e.g. a red dress, a blue shirt, etc.)"
                  className={styles.textInput}
                />
              </div>
              
              <div className={styles.controlGroup}>
                <label>Negative Prompt:</label>
                <input
                  type="text"
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                  placeholder="Unwanted elements (e.g. low quality, distortion, etc.)"
                  className={styles.textInput}
                />
              </div>
              
              <div className={styles.advancedToggle}>
                <button 
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className={styles.toggleButton}
                >
                  {showAdvanced ? 'Hide Advanced Settings ▲' : 'Show Advanced Settings ▼'}
                </button>
              </div>
              
              {showAdvanced && (
                <div className={styles.advancedSettings}>
                  <div className={styles.settingsGrid}>
                    <div className={styles.controlGroup}>
                      <label>Steps:</label>
                      <input
                        type="number"
                        min="10"
                        max="50"
                        value={steps}
                        onChange={(e) => setSteps(parseInt(e.target.value))}
                        className={styles.numberInput}
                      />
                    </div>
                    
                    <div className={styles.controlGroup}>
                      <label>Guidance Scale:</label>
                      <input
                        type="number"
                        min="1"
                        max="15"
                        step="0.5"
                        value={guidance}
                        onChange={(e) => setGuidance(parseFloat(e.target.value))}
                        className={styles.numberInput}
                      />
                    </div>
                    
                    <div className={styles.controlGroup}>
                      <label>Seed:</label>
                      <div className={styles.seedControl}>
                        <input
                          type="number"
                          value={seed}
                          onChange={(e) => setSeed(parseInt(e.target.value))}
                          className={styles.numberInput}
                        />
                        <button onClick={generateRandomSeed} className={styles.randomSeedBtn}>
                          <ThermometerSnowflake size={16} />
                        </button>
                      </div>
                    </div>
                    
                    <div className={`${styles.controlGroup} ${styles.checkbox}`}>
                      <label>
                        <input
                          type="checkbox"
                          checked={useAnimeSeg}
                          onChange={(e) => setUseAnimeSeg(e.target.checked)}
                        />
                        Use AnimeSeg
                      </label>
                    </div>
                    
                    <div className={`${styles.controlGroup} ${styles.checkbox}`}>
                      <label>
                        <input
                          type="checkbox"
                          checked={smoothMask}
                          onChange={(e) => setSmoothMask(e.target.checked)}
                        />
                        Smooth mask edges
                      </label>
                    </div>
                    
                    <div className={styles.controlGroup}>
                      <label>Mask Morphology:</label>
                      <select
                        value={morphOperation}
                        onChange={(e) => setMorphOperation(e.target.value)}
                        className={styles.selectInput}
                      >
                        <option value="none">None</option>
                        <option value="close">Close (fill small holes)</option>
                        <option value="open">Open (remove small objects)</option>
                        <option value="dilate">Dilate</option>
                        <option value="erode">Erode</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}
              
              <button
                onClick={handleProcessImage}
                disabled={isProcessing || brushCoordinates.length === 0}
                className={styles.primaryButton}
              >
                <Wand2 size={16} />
                {isProcessing ? 'Processing...' : 'Apply Outfit Change'}
              </button>
            </div>
            
            {resultImage && (
              <div className={styles.resultSection}>
                <h3>Result Image</h3>
                <div className={styles.resultImageContainer}>
                  <img src={resultImage} alt="Processed result" />
                </div>
                <button
                  onClick={continueEditingWithResult}
                  className={styles.continueButton}
                >
                  Continue Editing with This Result
                </button>
              </div>
            )}
          </section>
        )}
        
        {!originalImage && (
          <div className={styles.startInstruction}>
            <p>Upload an image to get started</p>
            <p className={styles.small}>Upload an anime character image and use the brush to mark the outfit area you want to change.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default OutfitEditor;