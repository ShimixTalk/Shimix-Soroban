import {createApplication,configuration} from '../server.mjs';
const cfg=configuration({SHIMIX_ORIGIN:'http://localhost',SHIMIX_BOOTSTRAP_TOKEN:'test-only-bootstrap-token-at-least-32-characters'});
cfg.localFile=':memory:';
const app=await createApplication(cfg);await new Promise(r=>app.server.listen(0,'127.0.0.1',r));cfg.origin=`http://localhost:${app.server.address().port}`;
console.log(JSON.stringify({origin:cfg.origin}));
process.on('SIGTERM',async()=>{await app.close();});
