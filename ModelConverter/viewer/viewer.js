var scene, camera, controls, renderer, modelGroup;
var offset = { x: 0, y: 0, z: 0 };
var enabledGeoms = {
    body: 1,
    Mane: 1,
    eyeball_l: 1,
    eyeball_r: 1,
};

function makeTextureMaterial(path, { repeat = 1, flipY = true } = {}) {
    var texture = new THREE.TextureLoader().load(path);
    
    if (repeat != 1) {
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.repeat.set(repeat, repeat);
    }
    
    texture.flipY = flipY;
    return new THREE.MeshLambertMaterial({
        map: texture,
        color: 0xffffff,
    });
}

function init() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera( 75, window.innerWidth / window.innerHeight, 0.1, 1000 );

    /*var geoms = parseSMDMesh(starlight_smd);
    var materials = {
        body: new THREE.MeshLambertMaterial( { color: 0xEDBBF3 } ),
        Mane: makeTextureMaterial('textures/mane.png'),
        eyeball_l: makeTextureMaterial('textures/pupil_l.png', {repeat: 2, flipY: false}),
        eyeball_r: makeTextureMaterial('textures/pupil_r.png', {repeat: 2, flipY: false}),
    };
    for(var name in geoms) {
        if (!enabledGeoms[name]) continue;
        console.log(name);
        var material = materials[name] || materials.body;
        var mesh = new THREE.Mesh( geoms[name], material );
        scene.add( mesh );
    }*/
    //material.wireframe = true;

    // Render the converted head into a group we can translate interactively.
    // The group's position IS the NECO_OFFSET applied by the converter, so
    // whatever offset looks right here is the value to bake in.
    modelGroup = new THREE.Group();
    scene.add(modelGroup);
    initModels(modelGroup);

    // Marker at the mesh origin (0,0,0): this is where the jaw bone attaches
    // in-game, so it stays fixed while the head moves around it.
    var originMarker = new THREE.Mesh(
        new THREE.SphereGeometry(0.01, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0xff3333 })
    );
    scene.add(originMarker);
    scene.add(new THREE.AxesHelper(0.25));
    
    var light = new THREE.AmbientLight( 0x404040 ); // soft white light
    scene.add( light );
    
    var directionalLight = new THREE.DirectionalLight( 0xffffff );
    directionalLight.position.set(10, 10, 5);
    // directionalLight.target = mesh;
    scene.add( directionalLight );
    
    /*var hlight = new THREE.HemisphereLight( 0xffffbb, 0x080820, 1 );
    scene.add( hlight );*/
    
    /*var light = new THREE.PointLight( 0xff0000, 0, 100 );
    light.position.set( 50, 50, 50 );
    scene.add( light );*/
    
    var gridHelper = new THREE.GridHelper( 10, 20 );
    scene.add( gridHelper )

    // To-scale kerbal reference. The grid (y=0) is ground level in-game, and a
    // kerbal is ~2.5 of our head-heights tall. The translucent body and the
    // green wireframe "head zone" show where the stock head sits; drag the Neco
    // Arc head so it fills the green box, then read off the offset.
    var HEAD_HEIGHT = 0.35;              // matches TARGET_HEIGHT in the converter
    var kerbalHeight = 2.5 * HEAD_HEIGHT;
    var neckY = kerbalHeight - HEAD_HEIGHT; // bottom of the head zone (~1.5 heads)

    var body = new THREE.Mesh(
        new THREE.BoxGeometry(0.22, neckY, 0.13),
        new THREE.MeshLambertMaterial({ color: 0x3377bb, transparent: true, opacity: 0.22 })
    );
    body.position.set(0, neckY / 2, 0);
    scene.add(body);

    var headZone = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(HEAD_HEIGHT, HEAD_HEIGHT, HEAD_HEIGHT)),
        new THREE.LineBasicMaterial({ color: 0x33ff88 })
    );
    headZone.position.set(0, neckY + HEAD_HEIGHT / 2, 0);
    scene.add(headZone);

    renderer = new THREE.WebGLRenderer({
        antialias: true,
    });
    renderer.setSize( window.innerWidth, window.innerHeight );
    let vs = viewSize();
    //renderer.setSize( vs.w, vs.h );
    renderer.setClearColor(0xcccccc);
    document.body.appendChild( renderer.domElement );

    controls = new THREE.OrbitControls( camera );
    controls.target = new THREE.Vector3( 0, 0.45, 0 );

    //controls.update() must be called after any manual changes to the camera's transform
    camera.position.set( 1.3, 0.9, 1.3 );
    controls.update();

    initOffsetControls();
}

function applyOffset() {
    if (modelGroup) {
        modelGroup.position.set(offset.x, offset.y, offset.z);
    }
    var readout = document.getElementById('offset-readout');
    if (readout) {
        var fmt = function (v) { return v.toFixed(3); };
        readout.textContent =
            'NECO_OFFSET_X = ' + fmt(offset.x) + '\n' +
            'NECO_OFFSET_Y = ' + fmt(offset.y) + '\n' +
            'NECO_OFFSET_Z = ' + fmt(offset.z) + '\n\n' +
            'deploy.ps1 -OffsetX ' + fmt(offset.x) +
            ' -OffsetY ' + fmt(offset.y) +
            ' -OffsetZ ' + fmt(offset.z);
    }
}

function bindOffsetAxis(axis) {
    var slider = document.getElementById('off-' + axis);
    var num = document.getElementById('num-' + axis);
    if (!slider || !num) return;

    // Dragging the slider updates the model and mirrors into the number box.
    slider.addEventListener('input', function () {
        var val = parseFloat(slider.value);
        if (isNaN(val)) return;
        offset[axis] = val;
        num.value = val;
        applyOffset();
    });

    // Typing in the number box updates the model and the slider, but must NOT
    // rewrite the box itself -- otherwise partial input like "0." is parsed to
    // 0 and the decimals you type get clobbered.
    num.addEventListener('input', function () {
        var val = parseFloat(num.value);
        if (isNaN(val)) return;
        offset[axis] = val;
        slider.value = val;
        applyOffset();
    });
}

function initOffsetControls() {
    ['x', 'y', 'z'].forEach(bindOffsetAxis);

    var reset = document.getElementById('offset-reset');
    if (reset) {
        reset.addEventListener('click', function () {
            ['x', 'y', 'z'].forEach(function (axis) {
                offset[axis] = 0;
                document.getElementById('off-' + axis).value = 0;
                document.getElementById('num-' + axis).value = 0;
            });
            applyOffset();
        });
    }

    applyOffset();
}

function animate() {

	requestAnimationFrame( animate );
    renderer.setSize( window.innerWidth, window.innerHeight );

	// required if controls.enableDamping or controls.autoRotate are set to true
	controls.update();

	renderer.render( scene, camera );

}

function docElem( property )
{
  var t
  return ((t = document.documentElement) || (t = document.body.parentNode)) && isNumber( t[property] ) ? t : document.body
}

// View width and height excluding any visible scrollbars
// http://www.highdots.com/forums/javascript/faq-topic-how-do-i-296669.html
//    1) document.client[Width|Height] always reliable when available, including Safari2
//    2) document.documentElement.client[Width|Height] reliable in standards mode DOCTYPE, except for Safari2, Opera<9.5
//    3) document.body.client[Width|Height] is gives correct result when #2 does not, except for Safari2
//    4) When document.documentElement.client[Width|Height] is unreliable, it will be size of <html> element either greater or less than desired view size
//       https://bugzilla.mozilla.org/show_bug.cgi?id=156388#c7
//    5) When document.body.client[Width|Height] is unreliable, it will be size of <body> element less than desired view size
function viewSize()
{
  // This algorithm avoids creating test page to determine if document.documentElement.client[Width|Height] is greater then view size,
  // will succeed where such test page wouldn't detect dynamic unreliability,
  // and will only fail in the case the right or bottom edge is within the width of a scrollbar from edge of the viewport that has visible scrollbar(s).
  var doc = docElem( 'clientWidth' ),
     body = document.body,
     w, h
  return isNumber( document.clientWidth ) ? { w : document.clientWidth, h : document.clientHeight } :
     doc === body
     || (w = Math.max( doc.clientWidth, body.clientWidth )) > self.innerWidth
     || (h = Math.max( doc.clientHeight, body.clientHeight )) > self.innerHeight ? { w : body.clientWidth, h : body.clientHeight } :
     { w : w, h : h }
}

function isNumber(x) {
    return typeof x == 'number';
}

init();
animate();